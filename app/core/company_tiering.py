"""
Тирование компаний — сравнение найденных компаний с базовым профилем.

5 тиров:
  Tier 1: делают то же самое в том же регионе
  Tier 2: делают то же самое в другом регионе
  Tier 3: похожий продукт, но другой positioning
  Tier 4: те же ключевые модули или интеграции
  Tier 5: похожие технические или бизнес-сигналы
"""

import os
import re
import json
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from app.core.base_results import scrapling_fetch_markdown

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


# ─── Парсинг similar_companies.md ───────────────────────────────────────────

def parse_similar_companies_md(md_path: str) -> list[dict]:
    """Извлекает компании из similar_companies.md."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    candidates = []
    # Ищем блоки: ## URL + GPT Summary
    pattern = r"##\s+(https?://[^\s]+)\s*\n+(.*?)(?=##\s+https|---\s*\n\*\*Total)"
    matches = re.findall(pattern, content, re.DOTALL)

    for url, block in matches:
        name = ""
        description = ""
        name_match = re.search(r"\*\*Name:\*\*\s*(.+)", block)
        desc_match = re.search(r"\*\*Description:\*\*\s*(.+)", block)
        if name_match:
            name = name_match.group(1).strip()
        if desc_match:
            description = desc_match.group(1).strip()

        candidates.append({
            "url": url.strip(),
            "name": name,
            "description": description,
        })

    return candidates


# ─── Сбор профилей компаний ────────────────────────────────────────────────

async def build_candidate_profile(url: str, candidate_info: dict) -> dict:
    """Спарсить сайт кандидата и построить компактный профиль через GPT-4o."""
    try:
        md = await scrapling_fetch_markdown(url)
    except Exception as e:
        print(f"  ⚠️ Не удалось спарсить {url}: {e}")
        return {"url": url, "error": str(e)}

    prompt = f"""
You are a company profile analyst. Analyze this company's website and return a structured profile.

Company URL: {url}
Known info from search: {json.dumps(candidate_info, ensure_ascii=False)}

Website content (markdown):
{md[:6000]}  # limit for context

Return ONLY a JSON object with these keys:
{{
  "name": "company name",
  "product_description": "1-2 sentences what they do",
  "vertical": "industry (HealthTech, FinTech, etc.)",
  "business_model": "B2B SaaS, B2C, Marketplace, etc.",
  "region": "headquarters location",
  "target_customers": "who are their clients",
  "key_features": ["list of main product features"],
  "tech_stack": ["technologies mentioned"],
  "integrations": ["third-party integrations mentioned"],
  "funding_stage": "seed/Series A/Series B+/unknown",
  "team_size": "number or range or unknown"
}}

Return ONLY the raw JSON object, no markdown formatting.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract structured company profiles from website content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        # Убираем markdown обёртку
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        profile = json.loads(raw)
        profile["url"] = url
        return profile

    except Exception as e:
        print(f"  ⚠️ Ошибка GPT для {url}: {e}")
        return {"url": url, "error": str(e), "raw": raw[:500] if 'raw' in dir() else ""}


# ─── Тирование ─────────────────────────────────────────────────────────────

TIERING_PROMPT = """
You are an expert B2B analyst. Compare a candidate company with a base company and assign it to the most appropriate tier.

TIER DEFINITIONS:

**Tier 1 — Same Product, Same Region:**
Candidate does essentially the same thing, for the same type of customers, in the same geographic region.
Example: Two telemedicine startups in Germany doing remote patient monitoring with IoT devices.

**Tier 2 — Same Product, Different Region:**
Candidate does essentially the same thing, but in a different geographic market.
Example: A telemedicine startup doing remote monitoring in the USA, while base is in Germany.

**Tier 3 — Similar Product, Different Positioning:**
Candidate has a similar core product but targets different customers, uses different business model, or positions differently.
Example: Base is B2B telemedicine, candidate is B2C telemedicine with same tech.

**Tier 4 — Same Key Modules or Integrations:**
Candidate uses similar key technologies, integrations, or modules, even if the overall product is different.
Example: Both use Bluetooth medical devices, or both integrate with Epic/HL7, or both use IoT sensors.

**Tier 5 — Similar Technical or Business Signals:**
Candidate shares some technical or business characteristics (tech stack, funding stage, team size, hiring patterns) but is not a direct competitor.

RULES:
- Assign ONLY ONE tier — the highest/most specific that applies
- Tier 1 is the most specific, Tier 5 is the broadest
- A company can only be in one tier
- If unsure between two tiers, pick the higher (more specific) one

BASE COMPANY PROFILE:
{base_profile}

CANDIDATE COMPANY PROFILE:
{candidate_profile}

Return ONLY a JSON object with this exact structure:
{{
  "tier": 1,
  "tier_name": "Same Product, Same Region",
  "reasoning": "2-3 sentences explaining why this tier was assigned, referencing specific matching or differentiating factors"
}}

Return ONLY the raw JSON object, no markdown formatting.
"""


def assign_tier(base_profile: dict, candidate_profile: dict) -> dict:
    """Присваивает тир кандидату через GPT-4o."""
    prompt = TIERING_PROMPT.format(
        base_profile=json.dumps(base_profile, ensure_ascii=False, indent=2),
        candidate_profile=json.dumps(candidate_profile, ensure_ascii=False, indent=2),
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You classify companies into tiers based on similarity to a base company."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        result = json.loads(raw)
        return result

    except Exception as e:
        print(f"  ⚠️ Ошибка тирования: {e}")
        return {
            "tier": 5,
            "tier_name": "Similar Signals (error in analysis)",
            "reasoning": f"Could not analyze: {str(e)[:200]}"
        }


# ─── Основной пайплайн тирования ──────────────────────────────────────────

TIER_NAMES = {
    1: "Same Product, Same Region",
    2: "Same Product, Different Region",
    3: "Similar Product, Different Positioning",
    4: "Same Key Modules/Integrations",
    5: "Similar Technical/Business Signals",
}


async def tier_companies(
    md_path: str,
    base_profile: dict,
    max_companies: int = 20,
) -> dict:
    """
    Полный пайплайн тирования:
      1. Парсим similar_companies.md
      2. Для каждой компании собираем профиль
      3. Сравниваем с базовым профилем
      4. Распределяем по тирам

    Возвращает:
    {
      "tier_1": { "name": "...", "companies": [...] },
      "tier_2": { ... },
      ...
      "summary": { "total": N, "tier_1": N, "tier_2": N, ... }
    }
    """
    # Шаг 1: Парсим MD
    candidates = parse_similar_companies_md(md_path)
    if not candidates:
        return {"error": "Не найдено компаний в similar_companies.md"}

    candidates = candidates[:max_companies]
    print(f"[Тирование] Найдено {len(candidates)} компаний")

    # Шаг 2: Собираем профили
    profiles = []
    for i, cand in enumerate(candidates):
        print(f"  [{i+1}/{len(candidates)}] Профиль: {cand['url']}")
        profile = await build_candidate_profile(cand["url"], cand)
        profiles.append(profile)

    # Шаг 3: Тирование
    tiers = {t: {"name": TIER_NAMES[t], "companies": []} for t in range(1, 6)}
    all_results = []

    for i, profile in enumerate(profiles):
        if "error" in profile:
            print(f"  [{i+1}] Пропуск (ошибка): {profile.get('url', 'unknown')}")
            continue

        print(f"  [{i+1}/{len(profiles)}] Тирование: {profile.get('name', profile.get('url', 'unknown'))}")
        tier_result = assign_tier(base_profile, profile)

        tier_num = tier_result.get("tier", 5)
        if tier_num not in tiers:
            tier_num = 5

        company_entry = {
            "url": profile.get("url", ""),
            "name": profile.get("name", ""),
            "description": profile.get("product_description", ""),
            "vertical": profile.get("vertical", ""),
            "region": profile.get("region", ""),
            "tier_reason": tier_result.get("reasoning", ""),
        }
        tiers[tier_num]["companies"].append(company_entry)
        all_results.append({**profile, "tier": tier_num, "tier_reason": tier_result.get("reasoning", "")})

    # Шаг 4: Summary
    summary = {"total": sum(len(t["companies"]) for t in tiers.values())}
    for t in range(1, 6):
        summary[f"tier_{t}"] = len(tiers[t]["companies"])

    return {
        "tier_1": tiers[1],
        "tier_2": tiers[2],
        "tier_3": tiers[3],
        "tier_4": tiers[4],
        "tier_5": tiers[5],
        "summary": summary,
        "all_companies": all_results,
    }


# ─── Генерация MD отчёта ──────────────────────────────────────────────────

def generate_tier_report(tier_data: dict, base_company_name: str) -> str:
    """Генерирует Markdown отчёт по тированию."""
    md = f"# Тирование компаний — {base_company_name}\n\n"
    md += "> Сравнение найденных компаний с базовым профилем\n\n"
    md += "---\n\n"

    summary = tier_data.get("summary", {})
    md += f"**Всего обработано:** {summary.get('total', 0)}\n\n"

    for t in range(1, 6):
        key = f"tier_{t}"
        tier = tier_data.get(key, {})
        count = summary.get(key, 0)
        name = tier.get("name", TIER_NAMES.get(t, f"Tier {t}"))

        md += f"## 🔹 Tier {t}: {name} ({count})\n\n"

        if not tier.get("companies"):
            md += "*Нет компаний*\n\n"
            continue

        for c in tier["companies"]:
            md += f"### {c.get('name', 'Unknown')}\n"
            md += f"- **URL:** {c.get('url', '')}\n"
            if c.get('description'):
                md += f"- **Описание:** {c['description']}\n"
            if c.get('vertical'):
                md += f"- **Vertical:** {c['vertical']}\n"
            if c.get('region'):
                md += f"- **Регион:** {c['region']}\n"
            if c.get('tier_reason'):
                md += f"- **Причина:** {c['tier_reason']}\n"
            md += "\n"

    return md


# ─── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    example_base = {
        "company_name": "MedKitDoc",
        "website": "https://interexy.com",
        "product_description": "Telemedicine app with Bluetooth medical device integration",
        "vertical": "HealthTech",
        "business_model": "B2B SaaS",
        "region": "Germany",
        "tech_stack": ["Swift", "Bluetooth"],
        "key_features": ["remote patient monitoring", "Bluetooth medical devices"],
    }

    result = asyncio.run(tier_companies("similar_companies.md", example_base))
    print(json.dumps(result, ensure_ascii=False, indent=2))

    report = generate_tier_report(result, "MedKitDoc")
    with open("tier_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("\n📄 Сохранён: tier_report.md")
