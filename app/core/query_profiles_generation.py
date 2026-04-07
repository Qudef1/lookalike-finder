import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are an expert in B2B lead generation and the technology market.
You generate precise, targeted Google search queries to find startup and company websites.
Goal: find startups and companies building similar products that may need external development teams.
Design queries that return actual company homepages, funding announcements, and startup profiles — NOT articles, lists, or directories.
Return ONLY a JSON object with 'queries' key containing an array of strings, without explanations.
"""

QUERY_GEN_USER = """
Based on the case profile, generate 15 highly targeted Google search queries to find websites of startups and companies building similar products.

Case Profile:
{case_profile}

RULES FOR QUERY GENERATION:

1. **Use `site:` operator for structured sources** (3-4 queries):
   - `site:crunchbase.com` — to find funded startups
   - `site:linkedin.com/company` — to find company pages
   - `site:angel.co` or `site:producthunt.com` — for startup discovery
   Example: `site:crunchbase.com telehealth remote patient monitoring seed funding`

2. **Focus on funding signals** (3-4 queries):
   - Include words: `funding`, `raised`, `seed`, `Series A`, `investment`
   - Combine with technology/vertical from the profile
   Example: `remote patient monitoring startup funding seed`

3. **Include technology + vertical combinations** (3-4 queries):
   - Use specific tech terms from the profile (e.g., `Bluetooth`, `IoT`, `AI`)
   - Combine with industry vertical and business model
   Example: `healthtech startup telemedicine B2B IoT Germany`

4. **Target hiring/outsource signals** (2-3 queries):
   - Include: `hiring`, `looking for developers`, `expanding team`, `CTO`
   Example: `B2B telemedicine startup hiring developers Germany`

5. **Geographic targeting** (1-2 queries):
   - Include region/country from profile
   Example: `healthtech startup Germany funding 2024`

CRITICAL RULES:
- DO NOT use generic terms like "company", "development", "software"
- Use SPECIFIC technical terms from the profile
- Each query should be 5-8 words max
- Queries must be in English
- Include a mix of: site: operators, funding signals, tech stack, vertical, geography
- Designed to return company homepages, not top lists or articles

EXAMPLE of excellent queries for a telehealth + Bluetooth + Germany profile:
[
  "site:crunchbase.com telehealth Bluetooth medical devices Germany",
  "remote patient monitoring startup funding seed",
  "B2B telemedicine startup Germany funding",
  "B2B SaaS medical devices startup funding raised",
  "healthtech startup telemedicine B2B IoT Germany",
  "site:linkedin.com/company telemedicine remote patient monitoring",
  "telemedicine Bluetooth wearables B2B startup hiring",
  "site:crunchbase.com digital health Germany seed funding",
  "remote monitoring IoT healthcare startup Series A",
  "B2B telemedicine platform Germany looking for developers"
]

Return a JSON object with key 'queries' containing an array of 15 strings.
"""

def generate_search_queries(case_profile: dict) -> list[str]:
    """Генерирует 15 поисковых запросов на основе профиля компании."""
    case_profile_str = json.dumps(case_profile, ensure_ascii=False, indent=2)
    user_prompt = QUERY_GEN_USER.format(case_profile=case_profile_str)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1500,
            temperature=0.6,
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
