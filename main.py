"""
Lookalike Finder — главный пайплайн.

Запуск:
    python main.py

Переменные окружения (.env):
    SERPER_API_KEY  — ключ от Serper.dev
    OPENAI_API_KEY  — ключ от OpenAI
"""

import os
import json
from app.core.company_profile import build_full_pipeline

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "app", "output")


def main(company_name: str = "Interexy MedKitDoc"):
    """Запуск пайплайна."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"[Пайплайн] Запуск для компании: {company_name}")

    result = build_full_pipeline(company_name)

    if "error" in result:
        print(f"[Ошибка] {result['error']}")
        return

    # Сохраняем результаты
    with open(os.path.join(OUTPUT_DIR, "company_profile.json"), "w", encoding="utf-8") as f:
        json.dump(result["profile"], f, ensure_ascii=False, indent=2)
    print(f"[Профиль] Сохранён: app/output/company_profile.json")

    with open(os.path.join(OUTPUT_DIR, "search_queries.json"), "w", encoding="utf-8") as f:
        json.dump(result["queries"], f, ensure_ascii=False, indent=2)
    print(f"[Запросы] Сохранены: app/output/search_queries.json")

    if "similar_companies_md" in result:
        with open(os.path.join(OUTPUT_DIR, "similar_companies.md"), "w", encoding="utf-8") as f:
            f.write(result["similar_companies_md"])
        print(f"[Компании] Сохранены: app/output/similar_companies.md")

    if "tier_report_md" in result:
        with open(os.path.join(OUTPUT_DIR, "tier_report.md"), "w", encoding="utf-8") as f:
            f.write(result["tier_report_md"])
        print(f"[Тирование] Сохранён: app/output/tier_report.md")

    if "tier_summary" in result:
        print(f"[Тирование] {json.dumps(result['tier_summary'], ensure_ascii=False)}")

    print("[Пайплайн] Завершён успешно")


if __name__ == "__main__":
    import sys
    company = sys.argv[1] if len(sys.argv) > 1 else "Interexy MedKitDoc"
    main(company)
