"""
Lookalike Finder — главный пайплайн.

Запуск:
    python main.py                                    # интерактивный режим
    python main.py "URL" "Company Name"              # быстрый запуск

Примеры:
    python main.py "https://interexy.com/case/medkitdoc" "MedKitDoc"
"""

import os
import sys
import json
from app.core.company_profile import build_full_pipeline


def main(case_url: str = None, company_name: str = None):
    """Запуск пайплайна."""
    # Интерактивный режим, если аргументы не переданы
    if not case_url or not company_name:
        print("🔍 Lookalike Finder — поиск похожих компаний")
        print("=" * 50)
        case_url = input("📎 URL страницы кейса: ").strip()
        company_name = input("🏢 Название компании: ").strip()

        if not case_url or not company_name:
            print("❌ URL и название компании обязательны.")
            return

    result = build_full_pipeline(case_url, company_name)

    if "error" in result:
        print(f"\n[Ошибка] {result['error']}")
        return

    # Вывод сводки
    print(f"\n📁 Папка кейса: {result['output_dir']}")
    print(f"📊 Тиры: {json.dumps(result.get('tier_summary', {}), ensure_ascii=False)}")
    print("\n✅ Готово!")


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        main(case_url=sys.argv[1], company_name=sys.argv[2])
    else:
        main()
