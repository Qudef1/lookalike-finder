import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are an expert in B2B lead generation and the technology market.
You generate precise search queries for Google (via Serper API) that target company websites.
Goal: find startups and companies building similar products that may need external development teams.
Focus on queries that return actual company homepages in search results, not lists or articles.
Return ONLY a JSON object with 'queries' key containing an array of strings, without explanations.
"""

QUERY_GEN_USER = """
Based on the case profile, generate 10 search queries for Google that will find websites of startups and companies building similar products.

Case Profile:
{case_profile}

Rules for queries:
- DO NOT use general words ("app development company")
- Use specific technical terms from the profile
- Cover different angles: by technology, by vertical, by stage, by hiring
- Some queries should search for companies at the stage of looking for developers (funding announcement, hiring CTO, MVP development)
- Include 2-3 queries with site:linkedin.com for startup search
- IMPORTANT: Queries must be designed to return company websites in organic search results, not top lists, articles, or directories. Focus on finding actual company homepages.

Example of good queries for telehealth + Bluetooth:
["B2B telemedicine Bluetooth medical devices mobile app startup 2024",
 "remote patient monitoring IoT mobile app seed funding",
 "telemedicine Bluetooth wearables B2B startup"]

Return a JSON object with key 'queries' containing an array of 10 strings.
"""

def generate_search_queries(case_profile: dict) -> list[str]:
    """Генерирует 10 поисковых запросов на основе профиля компании."""
    case_profile_str = json.dumps(case_profile, ensure_ascii=False, indent=2)
    user_prompt = QUERY_GEN_USER.format(case_profile=case_profile_str)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.5,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "search_queries",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "queries": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["queries"]
                    }
                }
            }
        )
        queries_json = response.choices[0].message.content.strip()
        if not queries_json:
            print("Пустой ответ от GPT")
            return []
        data = json.loads(queries_json)
        queries = data.get("queries", [])
        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            return queries
        else:
            print(f"Неверный формат ответа: {queries_json[:200]}")
            return []
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}, ответ: {queries_json[:200]}")
        return []
    except Exception as e:
        print(f"Ошибка при генерации запросов: {e}")
        return []

if __name__ == "__main__":
    # Пример профиля для тестирования
    example_profile = {
        "company_name": "MedKitDoc",
    "website": "https://interexy.com",
    "founded": "unknown",
    "stage": "seed",
    "total_funding": "€2.2M",
    "last_round": {
      "amount": "€1.7M",
      "date": "2021-05",
      "investors": [
        "Picus Capital",
        "Vorwerk Ventures",
        "Acton Capital"
      ]
    },
    "product_description": "MedKitDoc is a revolutionary telemedicine product focused on the B2B market, utilizing innovative Bluetooth-based MedKits to enable physicians to diagnose 49 more diseases than traditional telemedicine products.",
    "tech_stack_known": [
      "Swift",
      "Bluetooth"
    ],
    "team_size": "25-50",
    "key_people": [
      {
        "name": "unknown",
        "title": "unknown",
        "linkedin": "unknown"
      }
    ],
    "region": "Germany",
    "vertical": "HealthTech",
    "business_model": "B2B SaaS",
    "outsource_signals": [
      "We are hiring",
      "Partner with us"
    ]
  }
    queries = generate_search_queries(example_profile)
    print(json.dumps(queries, indent=2, ensure_ascii=False))
