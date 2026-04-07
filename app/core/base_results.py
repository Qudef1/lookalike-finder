import os
import json
import re
import requests
import asyncio
from dotenv import load_dotenv
from Scrapling.scrapling.core.ai import ScraplingMCPServer

load_dotenv()
SERPER_API = os.getenv("SERPER_API")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "app", "output")


def get_output_dir(case_name: str) -> str:
    """Создаёт и возвращает папку для кейса: app/output/{case_name}/."""
    safe_name = case_name.lower().replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')
    case_dir = os.path.join(OUTPUT_ROOT, safe_name)
    os.makedirs(case_dir, exist_ok=True)
    return case_dir

COMPANY_NAME = "Interexy MedKitDoc"


def clean_markdown_content(md_text: str) -> str:
    # 1. Удаляем все картинки: ![alt](url)
    md_text = re.sub(r'!\[.*?\]\(.*?\)', '', md_text)
    
    lines = md_text.split('\n')
    result = []
    
    # Флаги состояния
    in_menu_block = False
    
    # Ключевые слова корневых разделов меню (на основе вашего примера)
    # Приводим к нижнему регистру для сравнения
    root_menu_keywords = {
        "services", 
        "technology", 
        "tech stack", 
        "industries", 
        "company", 
        "portfolio", 
        "refer now",
        "blog"
    }
    
    # Уровень отступа, на котором началось меню, чтобы знать, когда оно закончилось
    # Но в Markdown отступы могут быть разными, поэтому лучше следить за структурой списков
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        lower_stripped = stripped.lower()
        
        # --- ЛОГИКА ОБНАРУЖЕНИЯ НАЧАЛА МЕНЮ ---
        
        # Паттерн 1: Корневой элемент списка "* Заголовок" (без ссылки, просто текст раздела)
        # Пример: "* Services" или "* Technology"
        is_root_list_item = re.match(r'^\*\s+([A-Za-z\s]+)$', stripped)
        
        if is_root_list_item and not in_menu_block:
            title = is_root_list_item.group(1).strip().lower()
            if title in root_menu_keywords:
                in_menu_block = True
                i += 1
                continue # Пропускаем эту строку
        
        # Паттерн 2: Ссылка-раздел "* [Title](#)" или "* [Title](/...)"
        # Пример: "* [Services](#)"
        is_root_link_item = re.match(r'^\*\s+\[(.*?)\]\(.*?\)$', stripped)
        if is_root_link_item and not in_menu_block:
            title = is_root_link_item.group(1).strip().lower()
            if any(k in title for k in root_menu_keywords):
                in_menu_block = True
                i += 1
                continue

        # --- ЛОГИКА НАХОЖДЕНИЯ ВНУТРИ МЕНЮ ---
        
        if in_menu_block:
            # Мы внутри меню. Проверяем, не конец ли это блока.
            
            # Конец меню обычно означает:
            # 1. Встретился заголовок статьи (начинается с #, но не внутри списка *)
            if re.match(r'^#[^#]', stripped) and not stripped.startswith('*'):
                in_menu_block = False
                result.append(line)
                i += 1
                continue
            
            # 2. Встретился обычный абзац текста (длинный, без маркеров списка)
            # Меню обычно состоит из коротких строк и ссылок. 
            # Если строка длинная (>100 символов), не начинается с * или +, и не является ссылкой - возможно, это статья.
            if len(stripped) > 100 and not re.match(r'^[\*\-\+]', stripped) and '[' not in stripped:
                # Дополнительная проверка: если это действительно начало статьи
                in_menu_block = False
                result.append(line)
                i += 1
                continue
            
            # 3. Проверка на вложенные элементы меню.
            # Если строка начинается с + или - (подпункты), или это пустая строка внутри блока - пропускаем.
            if re.match(r'^[\+\-]\s+', stripped) or stripped == "":
                i += 1
                continue
            
            # Если строка выглядит как продолжение списка (отступ), пропускаем
            # (В вашем примере подпункты имеют отступы)
            if line.startswith(' ') or line.startswith('\t'):
                 # Но осторожно: код статьи тоже может иметь отступы.
                 # Однако, если мы уже в режиме меню, и видим отступ + ссылку или короткий текст - это меню.
                 if '[' in stripped or len(stripped) < 60:
                     i += 1
                     continue
            
            # Если ничего не подошло, но флаг еще стоит - проверяем, не новая ли это секция меню
            # Иногда между секциями меню бывают разрывы. 
            # Если мы видим новый корневой элемент (* Services), мы уже обработали его выше, 
            # но если он идет сразу после другого без разрыва статьи - остаемся в режиме меню.
            
            # ПО УМОЛЧАНИЮ: Если мы в режиме меню и строка не похожа на начало статьи - пропускаем её.
            # Это агрессивная стратегия, но эффективная для чистки навигации.
            i += 1
            continue

        # Если мы НЕ в меню, добавляем строку в результат
        result.append(line)
        i += 1

    return "\n".join(result).strip()

# Пример использования в вашей функции
async def scrapling_fetch_markdown(url: str) -> str:
    response = await ScraplingMCPServer.get(
        url=url,
        extraction_type="markdown",
        main_content_only=True,
        follow_redirects=True,
        timeout=60,
    )
    
    raw_md = "".join(response.content).strip()
    clean_md = clean_markdown_content(raw_md)
    
    return clean_md

async def scrapling_fetch_markdown(url: str) -> str:
    response = await ScraplingMCPServer.get(
        url=url,
        extraction_type="markdown",
        main_content_only=True,
        follow_redirects=True,
        timeout=60,
    )
    
    raw_md = "".join(response.content).strip()
    clean_md = clean_markdown_content(raw_md)
    
    return clean_md

def serper_find_company_url(company_name: str) -> str | None:
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API,
        "Content-Type": "application/json",
    }
    payload = {"q": company_name}
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()

    # структура может быть: data["organic"][0]["link"] (более типично)
    if data and isinstance(data, dict):
        organic = data.get("organic") or []
        if organic and isinstance(organic, list):
            first = organic[0]
            if isinstance(first, dict) and first.get("link"):
                return first["link"]

        # запасной вариант (knowledgeGraph или searchResults)
        kg = data.get("knowledgeGraph", {})
        if isinstance(kg, dict) and kg.get("website"):
            return kg["website"]

    return None


def extract_domain(url: str) -> str:
    """Извлекает домен из URL для имени файла."""
    import re
    match = re.search(r'(?:https?://)?(?:www\.)?([^/:]+)', url)
    if match:
        return match.group(1).replace('.', '_')
    return "unknown"


async def return_company_markdown_from_url(url: str, case_name: str = "unknown") -> str:
    """Парсит сайт по прямому URL и сохраняет MD."""
    md = await scrapling_fetch_markdown(url)

    safe_name = case_name.lower().replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')
    output_path = os.path.join(get_output_dir(case_name), f"{safe_name}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    return md

async def scrapling_fetch_markdown(url: str) -> str:
    response = await ScraplingMCPServer.get(
        url=url,
        extraction_type="markdown",
        main_content_only=True,
        # Добавляем селекторы для исключения меню и навигации 
        follow_redirects=True,
        timeout=60,
    )
    
    markdown = "".join(response.content).strip()
    return clean_markdown_content(markdown)

def return_company_markdown(company_name: str = COMPANY_NAME):
    site_url = serper_find_company_url(company_name)
    if not site_url:
        raise RuntimeError("Не найден URL компании через Serper")

    print("Найдена компания:", site_url)

    md = asyncio.run(scrapling_fetch_markdown(site_url))
    
    with open(f"{company_name}.md", "w", encoding="utf-8") as f:
        f.write(md)

    return md


if __name__ == "__main__":
    return_company_markdown()