"""
Interexy Case Research — Web Search via OpenAI Responses API
Generates research_*.md files for each case using web search.
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OUTPUT_DIR = "research_output"

# 10 кейсов для research
CASES = [
    {
        "name": "MedKitDoc",
        "website": "https://apps.apple.com/de/app/medkitdoc/id1510720618",
        "industry": "Healthcare, Telemedicine",
        "location": "Germany (DACH)",
        "known_info": "Telemedicine app with Bluetooth medical device integration (oximeters, stethoscopes, blood pressure monitors). iOS app. Raised €2M funding."
    },
    {
        "name": "Metrikus",
        "website": "https://www.metrikus.io/",
        "industry": "Real Estate, IoT, PropTech",
        "location": "United Kingdom",
        "known_info": "Building efficiency platform. Normalizes data from sensors and BMS. Clients include Siemens, Philips, major universities. Space optimization, IAQ monitoring, ESG metrics."
    },
    {
        "name": "E.ON",
        "website": "https://www.eon.com/en.html",
        "industry": "Energy, Utilities",
        "location": "Germany (Essen)",
        "known_info": "One of Europe's largest energy companies. 50M+ customers in 30+ countries. We provided Data Engineer with Data Vault expertise for data warehousing and ETL."
    },
    {
        "name": "Fressnapf",
        "website": "https://www.fressnapf.de/",
        "industry": "E-commerce, IoT, Retail",
        "location": "Germany",
        "known_info": "Largest European pet store chain. We provide Backend Developer with LangChain/LangGraph for AI agents. E-commerce platform, online vet, pet insurance, IoT pet trackers."
    },
    {
        "name": "Compassly",
        "website": "https://crimsonheightsbh.com/",
        "industry": "Healthcare, Autism, Special Needs",
        "location": "USA (Utah)",
        "known_info": "App for people with autism. Integration with 80 hospitals. Time tracker for caregivers. Funded by Utah state government. Built from scratch with Node.js + React Native."
    },
    {
        "name": "Crumb",
        "website": "https://apps.apple.com/de/app/crumb/id1455844646",
        "industry": "Healthcare, Fitness, Wellness",
        "location": "Germany",
        "known_info": "Fitness app rewarding users for activities via local businesses. Top 17 in German AppStore Health & Fitness. 8000 active users, 4.7 rating. Government funding from Germany."
    },
    {
        "name": "Deverus",
        "website": "https://www.deverus.com/",
        "industry": "HR Tech, Background Screening, AI, Blockchain",
        "location": "Austin, USA",
        "known_info": "Background screening provider since 1998. 35K+ businesses, 2.5M employees/year. We built blockchain digital wallet (Polygon), AI chatbot with ML, legacy portal redesign."
    },
    {
        "name": "NXP Semiconductors",
        "website": "https://www.nxp.com/",
        "industry": "Semiconductors, Automotive, IoT",
        "location": "Netherlands (Eindhoven)",
        "known_info": "Global semiconductor company, spun off from Philips in 2006. Automotive electronics (ADAS), IoT, NFC. We provided Project Manager."
    },
    {
        "name": "Scale AI",
        "website": "https://scale.com/",
        "industry": "AI, Data Platform",
        "location": "San Francisco, USA",
        "known_info": "Leading AI data platform, $14B+ valuation. We provided 6 Python developers for client tasks."
    },
    {
        "name": "AcneAway (Honeydew)",
        "website": "https://honeydewcare.com/",
        "industry": "Healthcare, Telemedicine, Dermatology",
        "location": "New York, USA",
        "known_info": "Telehealth startup for acne care. Founded by businessman + dermatologist. We built MVP from scratch (PHP+Laravel, React.JS). Rebranded to Honeydew."
    }
]


def build_research_prompt(case):
    """Создаёт промпт для web research по кейсу"""
    
    return f"""You are an expert B2B researcher for Interexy, a software development company.

YOUR TASK:
Research the company "{case['name']}" thoroughly using web search. Find information that is NOT already known to us. 
Focus on publicly available data that would be useful for sales outreach and understanding the client better.

WHAT WE ALREADY KNOW (do NOT repeat this):
{case['known_info']}

Company website: {case['website']}
Industry: {case['industry']}
Location: {case['location']}

RESEARCH THE FOLLOWING (use web search for each section):

1. COMPANY OVERVIEW
- When founded, by whom
- Mission/vision
- Company size (employees, revenue if public)
- Funding history (rounds, amounts, investors)
- Key leadership (CEO, CTO, founders)

2. PRODUCT DEEP DIVE
- Main products/services (beyond what we know)
- Recent product launches or updates (2025-2026)
- Target customers / user base
- Pricing model if available
- Key integrations or partnerships

3. TECHNOLOGY & ENGINEERING
- Known tech stack (from job postings, BuiltWith, GitHub)
- Engineering team size
- Open source contributions
- Technical blog posts or talks

4. MARKET & COMPETITION
- Main competitors
- Market position (leader/challenger/niche)
- Market size and growth trends
- Key differentiators

5. RECENT NEWS & SIGNALS (2025-2026)
- Funding rounds
- Partnerships announced
- Product milestones
- Awards or recognition
- Executive changes
- Expansion (new markets, offices)
- Hiring trends (what roles are open)

6. INDUSTRY CONTEXT
- Key regulatory changes affecting them
- Industry trends relevant to their business
- Challenges typical for companies in this space

7. POTENTIAL INTEREXY VALUE
Based on your research, identify:
- Where they likely need development help
- Technical challenges they might face
- Expansion areas where Interexy expertise fits
- Specific Interexy cases/expertise that would be relevant

OUTPUT FORMAT:
Return a well-structured markdown document. Use headers (##) for each section.
Include specific facts, numbers, and dates where found.
Mark information you couldn't find as "[Not found in public sources]".
At the end, list all sources/URLs you referenced.

IMPORTANT: Focus on NEW information not in our "already known" section. Be specific with facts and numbers."""


def research_case(case):
    """Выполняет research одного кейса через OpenAI с web search"""
    
    print(f"\n   🔍 Researching: {case['name']}...")
    
    prompt = build_research_prompt(case)
    
    url = "https://api.openai.com/v1/responses"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o",
        "tools": [{"type": "web_search"}],
        "input": prompt
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        
        if response.status_code != 200:
            print(f"      ❌ OpenAI error: {response.status_code}")
            print(f"      Response: {response.text[:500]}")
            return None
        
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
            return None
        
        print(f"      ✅ Research complete ({len(output_text)} chars)")
        return output_text
        
    except requests.exceptions.Timeout:
        print(f"      ❌ Timeout (180s)")
        return None
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return None


def save_research(case_name, research_text):
    """Сохраняет research в .md файл"""
    
    safe_name = case_name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
    filename = f"research_{safe_name}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    header = f"""# {case_name} — Web Research

> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> Source: OpenAI GPT-4o with web search
> Purpose: Interexy knowledge base enrichment

---

"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(header + research_text)
    
    print(f"      💾 Saved: {filepath}")
    return filepath


def main():
    print("=" * 100)
    print("🔬 INTEREXY CASE RESEARCH — Web Search Pipeline")
    print("=" * 100)
    print(f"   Cases to research: {len(CASES)}")
    print(f"   Model: gpt-4o with web search")
    print(f"   Output: {OUTPUT_DIR}/")
    print(f"   Estimated time: ~2-3 min per case")
    print(f"   Estimated cost: ~$0.10-0.20 per case")
    
    if not OPENAI_API_KEY:
        print("\n❌ OPENAI_API_KEY not found in .env!")
        print("   Add OPENAI_API_KEY=sk-proj-... to your .env file")
        exit(1)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    results = {
        'successful': 0,
        'failed': 0,
        'files': []
    }
    
    start_time = time.time()
    
    for idx, case in enumerate(CASES, 1):
        print(f"\n{'='*80}")
        print(f"[{idx}/{len(CASES)}] {case['name']} ({case['industry']})")
        print(f"{'='*80}")
        
        research_text = research_case(case)
        
        if research_text:
            filepath = save_research(case['name'], research_text)
            results['successful'] += 1
            results['files'].append(filepath)
        else:
            results['failed'] += 1
            print(f"      ⚠️ Skipping {case['name']}")
        
        # Rate limiting — пауза между запросами
        if idx < len(CASES):
            print(f"      ⏸️  Пауза 5 сек...")
            time.sleep(5)
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 100)
    print("✅ RESEARCH COMPLETE")
    print("=" * 100)
    print(f"   Successful: {results['successful']}/{len(CASES)}")
    print(f"   Failed: {results['failed']}/{len(CASES)}")
    print(f"   Time: {int(elapsed/60)} min {int(elapsed%60)} sec")
    print(f"   Est. cost: ~${results['successful'] * 0.15:.2f}")
    
    if results['files']:
        print(f"\n   📁 Generated files:")
        for f in results['files']:
            print(f"      • {f}")
    
    print(f"\n   Next step: copy research_output/*.md to MongoDB-RAG-Agent/documents/")
    print("=" * 100)


if __name__ == "__main__":
    main()


