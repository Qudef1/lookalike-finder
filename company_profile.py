import os
import json
import requests
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from base_results import return_company_markdown
from query_profiles_generation import generate_search_queries
from sites_finder import find_similar_companies

load_dotenv()
SERPER_API = os.getenv("SERPER_API")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def serper_search_additional_info(company_name: str) -> str:
    """Ищет дополнительную информацию по компании через Serper."""
    # Подумать про то какие вообще воозможные запросы могут быть полезны для получения информации о компании. Например:
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
            snippets = [item.get("snippet", "") for item in organic[:3]]  # первые 3 результата
            all_results.extend(snippets)
        except Exception as e:
            print(f"Ошибка при поиске для {query}: {e}")
    return "\n".join(all_results)

def build_company_profile(company_name: str) -> dict:
    """Строит профиль компании на основе MD файла и дополнительной информации."""
    # Получить MD из сайта
    md_content = return_company_markdown(company_name)
    
    # Получить дополнительную информацию через Serper
    additional_info = serper_search_additional_info(company_name)
    
    # Промпт для GPT-4o
    prompt = f"""
Act as a Senior Market Intelligence Analyst. Your task is to extract structured data from the provided Markdown content and additional search results to create a comprehensive company profile.

Markdown Content:
{md_content}

Additional Search Information:
{additional_info}

### Instructions:
1. **Extraction & Inference**: Extract explicit data where available. If specific data points (like funding or team size) are not explicitly stated, look for strong signals to make a logical inference (e.g., "We are hiring 50+ engineers" implies team size > 50; "Staff Augmentation" services imply an outsource business model). If no information or strong signals exist, use "unknown" or empty arrays.
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
        # Убедимся, что это JSON
        profile = json.loads(profile_json)
        return profile
    except Exception as e:
        print(f"Ошибка при генерации профиля: {e}")
        return {}

def build_full_pipeline(company_name: str) -> dict:
    """Полный пайплайн: профиль -> запросы -> поиск похожих компаний."""
    # Шаг 1: Построить профиль
    profile = build_company_profile(company_name)
    if not profile:
        return {"error": "Не удалось построить профиль"}
    
    # Шаг 2: Генерировать поисковые запросы
    queries = generate_search_queries(profile)
    if not queries:
        return {"profile": profile, "error": "Не удалось сгенерировать запросы"}
    
    # Шаг 3: Найти похожие компании
    similar_md = asyncio.run(find_similar_companies(queries))
    
    return {
        "profile": profile,
        "queries": queries,
        "similar_companies_md": similar_md
    }

if __name__ == "__main__":
    company_name = "Interexy MedKitDoc"
    result = build_full_pipeline(company_name)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    # Сохранить MD в файл
    if "similar_companies_md" in result:
        with open("similar_companies.md", "w", encoding="utf-8") as f:
            f.write(result["similar_companies_md"])
