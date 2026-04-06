"""
Lookalike Finder — главный пайплайн.

Запуск:
    python main.py

Переменные окружения (.env):
    SERPER_API_KEY  — ключ от Serper.dev
    OPENAI_API_KEY  — ключ от OpenAI
"""

import json
from company_profile import build_full_pipeline


def main():
    company_name = "Interexy MedKitDoc"

    print(f"[Пайплайн] Запуск для компании: {company_name}")

    result = build_full_pipeline(company_name)

    if "error" in result:
        print(f"[Ошибка] {result['error']}")
        return

    # Сохраняем результаты
    with open("company_profile.json", "w", encoding="utf-8") as f:
        json.dump(result["profile"], f, ensure_ascii=False, indent=2)
    print(f"[Профиль] Сохранён: company_profile.json")

    with open("search_queries.json", "w", encoding="utf-8") as f:
        json.dump(result["queries"], f, ensure_ascii=False, indent=2)
    print(f"[Запросы] Сохранены: search_queries.json")

    if "similar_companies_md" in result:
        with open("similar_companies.md", "w", encoding="utf-8") as f:
            f.write(result["similar_companies_md"])
        print(f"[Компании] Сохранены: similar_companies.md")

    print("[Пайплайн] Завершён успешно")


if __name__ == "__main__":
    main()
