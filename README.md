# 🔍 Lookalike Finder

Поиск компаний, похожих по профилю, с автоматическим тированием.

## Структура проекта

```
lookalike-finder/
├── main.py                          # CLI входная точка
├── .env                             # OPENAI_API_KEY
├── pyproject.toml                   # зависимости
│
├── app/
│   ├── core/                        # бизнес-логика
│   │   ├── base_results.py          # Scrapling парсинг, Serper поиск
│   │   ├── company_profile.py       # построение профиля компании
│   │   ├── query_profiles_generation.py  # генерация поисковых запросов
│   │   ├── sites_finder.py          # поиск кандидатов (GPT-4o + web search)
│   │   └── company_tiering.py       # тирование компаний
│   │
│   ├── api/
│   │   └── server.py                # FastAPI сервер + веб-интерфейс
│   │
│   └── output/                      # результаты пайплайна
│       ├── company_profile.json
│       ├── search_queries.json
│       ├── similar_companies.md
│       └── tier_report.md
│
└── examples/                        # примеры профилей
```

## Пайплайн

```
1. build_company_profile()    → JSON-профиль компании
2. generate_search_queries()  → 15 поисковых запросов
3. find_similar_companies()   → GPT-4o web search + парсинг сайтов
4. tier_companies()           → распределение по 5 тирам
```

### Тиры

| Тир | Описание |
|-----|----------|
| **Tier 1** | Тот же продукт, тот же регион |
| **Tier 2** | Тот же продукт, другой регион |
| **Tier 3** | Похожий продукт, другой positioning |
| **Tier 4** | Те же ключевые модули/интеграции |
| **Tier 5** | Похожие технические/бизнес-сигналы |

## Установка

```bash
python -m venv venv && source venv/bin/activate
pip install openai python-dotenv requests fastapi uvicorn[standard]
```

Создайте `.env`:
```
OPENAI_API_KEY=sk-proj-...
```

## Запуск

### CLI

```bash
python main.py                           # по умолчанию
python main.py "Interexy MedKitDoc"      # конкретная компания
```

### API сервер

```bash
uvicorn app.api.server:app --reload --port 8000
```

Откройте http://localhost:8000 — веб-интерфейс + Swagger docs на http://localhost:8000/docs

### API эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/run` | Запустить пайплайн |
| `GET`  | `/api/jobs` | Список всех задач |
| `GET`  | `/api/jobs/{id}` | Статус и результат |

Пример:
```bash
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Interexy MedKitDoc"}'
```

## Стоимость

~$0.50 за один кейс (GPT-4o + web_search tool).
Время выполнения: 12–22 минуты.
