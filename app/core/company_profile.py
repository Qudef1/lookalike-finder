"""
Company Profile — полный пайплайн: профиль → запросы → поиск → тирование.
"""

import os
import json
import requests
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from app.core.base_results import get_output_dir, return_company_markdown_from_url
from app.core.query_profiles_generation import generate_search_queries
from app.core.sites_finder import find_similar_companies
from app.core.company_tiering import tier_companies, generate_tier_report

load_dotenv()
SERPER_API = os.getenv("SERPER_API")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def serper_search_additional_info(company_name: str) -> str:
    """Ищет дополнительную информацию по компании через Serper."""
    queries = [
        f"{company_name} funding",
        f"{company_name} investors",
        f"{company_name} team",
        f"{company_name} product"
    ]
    all_results = []
    for query in queries:
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": SERPER_API,
            "Content-Type": "application/json",
        }
        payload = {"q": query}
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            r.raise_for_status()
            data = r.json()
            organic = data.get("organic", [])
            snippets = [item.get("snippet", "") for item in organic[:3]]
            all_results.extend(snippets)
        except Exception as e:
            print(f"Ошибка при поиске для {query}: {e}")
    return "\n".join(all_results)


def build_company_profile(case_url: str, company_name: str, case_name: str) -> dict:
    """
    Строит профиль компании по прямому URL кейса.

    Args:
        case_url: URL страницы кейса (например, https://interexy.com/case/medkitdoc)
        company_name: название компании-клиента (например, "MedKitDoc")
        case_name: имя для папки вывода (например, "medkitdoc")
    """
    # Шаг 1: Парсим сайт кейса по URL
    md_content = asyncio.run(return_company_markdown_from_url(case_url, case_name))

    # Шаг 2: Ищем доп. информацию через Serper
    additional_info = serper_search_additional_info(company_name)

    # Шаг 3: GPT-4o строит JSON-профиль
    prompt = f"""
Act as a Senior Market Intelligence Analyst from Interexy Company. Your task is to extract structured data from the provided Markdown content and additional search results to create a comprehensive company profile.
You need to make profile of company that Interexy was working with. You have a case in which described what especially Interexy did for this company, what was the project about, what technologies were used, how big was the team and etc. You need to extract all possible information from this case and also use additional search results to fill in the gaps.
Do not make profile of Interexy.

Markdown Content (from case page {case_url}):
{md_content}

Additional Search Information:
{additional_info}

### Instructions:
1. **Extraction & Inference**: Extract explicit data where available. If specific data points (like funding or team size) are not explicitly stated, look for strong signals to make a logical inference. If no information or strong signals exist, use "unknown" or empty arrays.
2. **Normalization**:
   - Dates should be in "YYYY" or "YYYY-MM" format.
   - Funding amounts should include currency (e.g., "$2.5M", "€500K").
   - "Vertical" must be specific (e.g., "FinTech", "HealthTech", "Logistics") rather than generic "IT".
   - "Business Model" should define how they make money (e.g., "B2B SaaS", "Service-based/Outsource", "Marketplace").
3. **Outsource Signals**: Specifically look for phrases like "Staff Augmentation", "Dedicated Teams", "Hiring", "Careers", or "Partner with us" to populate the `outsource_signals` array.
4. **Output Format**: Return ONLY a valid, raw JSON object. Do not include markdown code blocks (```json), explanations, or any text outside the JSON structure.

### JSON Schema:
{{
  "company_name": "string (Official legal name or brand name)",
  "website": "string (Primary domain URL)",
  "founded": "string (Year or 'unknown')",
  "stage": "string (seed / Series A / Series B+ / scaleup / enterprise / bootstrapped / unknown)",
  "total_funding": "string (Total amount raised or 'unknown')",
  "last_round": {{
    "amount": "string (Amount or 'unknown')",
    "date": "string (Date or 'unknown')",
    "investors": ["list of investor names"]
  }},
  "product_description": "string (Concise 2-3 sentence summary of core value proposition)",
  "tech_stack_known": ["list of specific technologies mentioned, e.g., Python, React, AWS"],
  "team_size": "string (Exact number, range like '50-100', or 'unknown')",
  "key_people": [
    {{
      "name": "string",
      "title": "string",
      "linkedin": "string (URL or 'unknown')"
    }}
  ],
  "region": "string (Headquarters location, e.g., 'New York, USA' or 'Remote-first')",
  "vertical": "string (Primary industry focus)",
  "business_model": "string (e.g., B2B Service, SaaS, Hybrid)",
  "outsource_signals": ["list of specific phrases or sections indicating openness to outsourcing or hiring"]
}}

RETURN ONLY THE RAW JSON OBJECT WITHOUT ANY EXPLANATIONS OR MARKDOWN FORMATTING.
Generate the JSON now:
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates company profiles in JSON format."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        profile_json = response.choices[0].message.content.strip()
        profile = json.loads(profile_json)

        # Сохраняем профиль в папку кейса
        output_dir = get_output_dir(case_name)
        safe_name = case_name.lower().replace(' ', '_').replace('/', '_')
        profile_path = os.path.join(output_dir, f"{safe_name}_profile.json")
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=4, ensure_ascii=False)
        print(f"  💾 Профиль сохранён: {profile_path}")

        return profile
    except Exception as e:
        print(f"Ошибка при генерации профиля: {e}")
        return {}


def build_full_pipeline(case_url: str, company_name: str) -> dict:
    """
    Полный пайплайн: профиль → запросы → поиск → тирование.

    Args:
        case_url: URL страницы кейса (например, https://interexy.com/case/medkitdoc)
        company_name: название компании-клиента (например, "MedKitDoc")
    """
    case_name = company_name  # имя папки = название компании

    print(f"\n{'='*60}")
    print(f"[Пайплайн] Кейс: {company_name}")
    print(f"[Пайплайн] URL:  {case_url}")
    print(f"{'='*60}")

    # Создаём папку кейса
    output_dir = get_output_dir(case_name)
    safe_name = case_name.lower().replace(' ', '_').replace('/', '_')

    # ── Шаг 1: Профиль ──────────────────────────────────────────
    print("\n[1/4] Построение профиля компании...")
    profile = build_company_profile(case_url, company_name, case_name)
    if not profile:
        return {"error": "Не удалось построить профиль"}

    # ── Шаг 2: Поисковые запросы ────────────────────────────────
    print("\n[2/4] Генерация поисковых запросов...")
    queries = generate_search_queries(profile)
    if not queries:
        return {"profile": profile, "error": "Не удалось сгенерировать запросы"}

    # Сохраняем запросы
    queries_path = os.path.join(output_dir, f"search_queries_{safe_name}.json")
    with open(queries_path, "w", encoding="utf-8") as f:
        json.dump(queries, f, ensure_ascii=False, indent=2)
    print(f"  💾 Запросы сохранены: {queries_path}")

    # ── Шаг 3: Поиск похожих компаний ────────────────────────────
    print("\n[3/4] Поиск похожих компаний...")
    similar_md = asyncio.run(find_similar_companies(queries, case_profile=profile))

    # Сохраняем похожие компании
    similar_path = os.path.join(output_dir, f"similar_companies_{safe_name}.md")
    with open(similar_path, "w", encoding="utf-8") as f:
        f.write(similar_md)
    print(f"  💾 Похожие компании: {similar_path}")

    # ── Шаг 4: Тирование ─────────────────────────────────────────
    print("\n[4/4] Тирование компаний...")
    tier_result = asyncio.run(tier_companies(similar_path, profile, case_name=case_name))

    tier_report_md = generate_tier_report(tier_result, company_name)

    # Сохраняем отчёт тирования
    tier_path = os.path.join(output_dir, f"tier_report_{safe_name}.md")
    with open(tier_path, "w", encoding="utf-8") as f:
        f.write(tier_report_md)
    print(f"  💾 Отчёт тирования: {tier_path}")

    # ── Итог ─────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"[Пайплайн] Завершён успешно")
    print(f"[Пайплайн] Все файлы: {output_dir}/")
    print(f"{'='*60}")

    return {
        "output_dir": output_dir,
        "profile": profile,
        "queries": queries,
        "similar_companies_md": similar_md,
        "tier_report_md": tier_report_md,
        "tier_summary": tier_result.get("summary", {}),
        "tiers": {f"tier_{t}": tier_result.get(f"tier_{t}", {}).get("companies", []) for t in range(1, 6)},
    }
