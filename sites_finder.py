import os
import json
import requests
import asyncio
from dotenv import load_dotenv
from base_results import clean_markdown_content, scrapling_fetch_markdown

load_dotenv()
SERPER_API = os.getenv("SERPER_API")

def serper_search_companies(query: str, max_results: int = 10) -> list[str]:
    """Ищет компании через Serper и возвращает список URL."""
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API,
        "Content-Type": "application/json",
    }
    payload = {"q": query, "num": max_results}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        organic = data.get("organic", [])
        links = [item.get("link") for item in organic if item.get("link")]
        return links
    except Exception as e:
        print(f"Ошибка при поиске для {query}: {e}")
        return []

async def parse_company_site(url: str) -> str:
    """Парсит сайт компании и возвращает очищенный MD."""
    try:
        md = await scrapling_fetch_markdown(url)
        return md
    except Exception as e:
        print(f"Ошибка при парсинге {url}: {e}")
        return ""

def extract_company_summary(md: str, url: str) -> str:
    """Извлекает краткое описание компании из MD."""
    # Простая экстракция: первые 500 символов или заголовки
    lines = md.split('\n')  # Первые 10 строк

    summary = '\n'.join(lines).strip()

    return f"**{url}**\n{summary}\n\n"

async def find_similar_companies(queries: list[str]) -> str:
    """Находит похожие компании по запросам и возвращает MD документ."""
    all_companies_md = "# Найденные похожие компании\n\n"
    seen_urls = set()  # Чтобы избежать дубликатов
    
    int = 0



    for query in queries:
        int += 1
        print(f"Поиск по запросу: {query}")
        urls = serper_search_companies(query)
        for url in urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            print(f"Парсинг: {url}")
            md = await parse_company_site(url)
            if md:
                summary = extract_company_summary(md, url)
                all_companies_md += summary
        
        
        
        
        if int == 1:
            break 






    return all_companies_md

if __name__ == "__main__":
    # Пример запросов для тестирования
    example_queries = [
        "B2B telemedicine Bluetooth medical devices mobile app startup 2024",
        "remote patient monitoring IoT mobile app seed funding Germany",
        "site:linkedin.com telemedicine Bluetooth wearables B2B startup"
    ]
    md_result = asyncio.run(find_similar_companies(example_queries))
    print(md_result)
    # Сохранить в файл
    with open("similar_companies.md", "w", encoding="utf-8") as f:
        f.write(md_result)
