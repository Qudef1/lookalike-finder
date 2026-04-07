"""
Поиск похожих компаний через GPT-4o с web search.
Заменяет Serper на OpenAI Responses API с инструментом web_search.
"""

import os
import json
import time
import asyncio
import requests
from dotenv import load_dotenv
from app.core.base_results import clean_markdown_content, scrapling_fetch_markdown

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def search_candidates_via_gpt(query: str, case_profile: dict = None) -> list[dict]:
    """
    Использует GPT-4o с web search для поиска кандидатов по запросу.
    Возвращает список кандидатов с URL и кратким описанием.
    """
    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    context_info = ""
    if case_profile:
        context_info = f"""
Context about the type of companies we're looking for:
- Profile: {json.dumps(case_profile, ensure_ascii=False, indent=2)}
Focus on finding companies that match this profile.
"""

    prompt = f"""
You are an expert B2B researcher. Search the web using this query to find startup/company websites:

Search Query: {query}
{context_info}

YOUR TASK:
Search for companies/startups that match this query. Focus on finding actual company websites, not articles or directories.

Return your findings as a JSON array with this exact structure for each company:
[
  {{
    "name": "Company Name",
    "url": "https://company-website.com",
    "description": "Brief 1-2 sentence description of what they do",
    "relevance_reason": "Why this company matches the search query"
  }}
]

RULES:
- Return ONLY valid JSON array, no explanations or markdown
- Include 3-5 most relevant companies
- URLs must be actual company homepages, not LinkedIn/Crunchbase profiles
- Focus on startups and small/medium companies that might need external development help
- Exclude large enterprises (Fortune 500, etc.)
"""

    payload = {
        "model": "gpt-4o",
        "tools": [{"type": "web_search"}],
        "input": prompt
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)

        if response.status_code != 200:
            print(f"      ❌ OpenAI error: {response.status_code}")
            print(f"      Response: {response.text[:500]}")
            return []

        data = response.json()

        # Извлекаем текст из response
        output_array = data.get('output', [])
        output_text = ""

        for item in output_array:
            if item.get('type') == 'message':
                content_array = item.get('content', [])
                for content_item in content_array:
                    if content_item.get('type') == 'output_text':
                        output_text = content_item.get('text', '')
                        break
                if output_text:
                    break

        if not output_text:
            print(f"      ❌ No output text received")
            return []

        # Парсим JSON из ответа
        output_text = output_text.strip()
        # Убираем возможные markdown маркеры
        if output_text.startswith("```json"):
            output_text = output_text[7:]
        if output_text.endswith("```"):
            output_text = output_text[:-3]
        output_text = output_text.strip()

        try:
            candidates = json.loads(output_text)
            if isinstance(candidates, list):
                return candidates
            else:
                print(f"      ⚠️ Unexpected JSON structure")
                return []
        except json.JSONDecodeError as e:
            print(f"      ❌ JSON parse error: {e}")
            print(f"      Raw output: {output_text[:200]}")
            return []

    except requests.exceptions.Timeout:
        print(f"      ❌ Timeout (120s)")
        return []
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return []


async def parse_company_site(url: str) -> str:
    """Парсит сайт компании и возвращает очищенный MD."""
    try:
        md = await scrapling_fetch_markdown(url)
        return md
    except Exception as e:
        print(f"Ошибка при парсинге {url}: {e}")
        return ""


def extract_company_summary(md: str, url: str, candidate_info: dict = None) -> str:
    """Извлекает краткое описание компании из MD."""
    lines = md.split('\n')
    summary = '\n'.join(lines[:20]).strip()  # Первые 20 строк для контекста

    extra_info = ""
    if candidate_info:
        name = candidate_info.get('name', '')
        description = candidate_info.get('description', '')
        if name or description:
            extra_info = f"\n\n**GPT Summary:**\n"
            if name:
                extra_info += f"- **Name:** {name}\n"
            if description:
                extra_info += f"- **Description:** {description}\n"

    return f"## {url}\n{extra_info}\n{summary}\n\n---\n\n"


async def find_similar_companies(queries: list[str], case_profile: dict = None, max_candidates_per_query: int = 3) -> str:
    """
    Находит похожие компании по запросам через GPT-4o web search.
    Возвращает MD документ с результатами.
    """
    all_companies_md = "# Найденные похожие компании\n\n"
    all_companies_md += f"> Generated via GPT-4o web search\n"
    all_companies_md += f"> Search queries: {len(queries)}\n\n"
    all_companies_md += "---\n\n"

    seen_urls = set()
    total_candidates = 0
    query_count = 0

    for query in queries:
        query_count += 1
        print(f"[{query_count}/{len(queries)}] Поиск по запросу: {query}")

        # Шаг 1: GPT ищет кандидатов через web search
        candidates = search_candidates_via_gpt(query, case_profile)

        if not candidates:
            print(f"      ⚠️ Найдено 0 кандидатов")
            continue

        print(f"      ✅ Найдено {len(candidates)} кандидатов")

        # Шаг 2: Парсим сайты кандидатов для получения доп. информации
        candidates_processed = 0
        for candidate in candidates:
            url = candidate.get('url', '')
            if not url or url in seen_urls:
                continue

            seen_urls.add(url)
            print(f"      Парсинг: {url}")

            md = await parse_company_site(url)
            if md:
                summary = extract_company_summary(md, url, candidate)
                all_companies_md += summary
                total_candidates += 1
                candidates_processed += 1

            # Лимит кандидатов на запрос
            if candidates_processed >= max_candidates_per_query:
                break

        # Rate limiting между запросами
        if query_count < len(queries):
            await asyncio.sleep(3)

    all_companies_md += f"\n\n---\n**Total companies found:** {total_candidates}\n"
    all_companies_md += f"**Unique URLs:** {len(seen_urls)}\n"

    return all_companies_md


if __name__ == "__main__":
    # Пример запросов для тестирования
    example_queries = [
        "site:crunchbase.com telehealth Bluetooth medical devices Germany",
        "remote patient monitoring startup funding seed",
        "B2B telemedicine startup Germany funding",
    ]

    example_profile = {
        "company_name": "MedKitDoc",
        "website": "https://interexy.com",
        "stage": "seed",
        "total_funding": "€2.2M",
        "product_description": "Telemedicine product focused on B2B market, utilizing Bluetooth-based MedKits",
        "region": "Germany",
        "vertical": "HealthTech",
        "business_model": "B2B SaaS",
    }

    md_result = asyncio.run(find_similar_companies(example_queries, example_profile))
    print(md_result)

    # Сохранить в файл
    with open("similar_companies.md", "w", encoding="utf-8") as f:
        f.write(md_result)
