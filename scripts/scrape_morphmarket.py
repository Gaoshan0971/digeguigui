#!/usr/bin/env python3
"""爬取 MorphMarket / World of Ball Pythons morph 数据"""
import requests, json, re, time, sys, os
from bs4 import BeautifulSoup

BASE = "https://www.morphmarket.com"
HEADERS = {"User-Agent": "Digeguigui/2.0 (research; contact@digeguigui.com)"}
PROJ = "/home/ubuntu/digeguigui"
OUT = os.path.join(PROJ, "data", "morphmarket_raw.json")
results = []

def scrape_category(url, species_name, category="snake"):
    """爬取品系列表页"""
    print(f"[{species_name}] {url}", flush=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}", flush=True)
            return []
        soup = BeautifulSoup(r.text, 'html.parser')
        morphs = []
        for link in soup.select('a[href*="/morphs/"]'):
            href = link.get('href', '')
            name = link.get_text(strip=True)
            if name and '/morphs/' in href and name not in ('Morphs', 'Traits', ''):
                morphs.append({"name": name, "url": BASE + href, "species": species_name, "category": category})
        seen = set()
        unique = []
        for m in morphs:
            if m['name'] not in seen:
                seen.add(m['name'])
                unique.append(m)
        print(f"  → {len(unique)} morphs", flush=True)
        return unique
    except Exception as e:
        print(f"  Error: {e}", flush=True)
        return []

# Also try World of Ball Pythons
def scrape_wobp():
    """爬取 World of Ball Pythons morph list"""
    url = "https://www.worldofballpythons.com/morphs/"
    print(f"[球蟒(WOBP)] {url}", flush=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}", flush=True)
            return []
        soup = BeautifulSoup(r.text, 'html.parser')
        morphs = []
        for link in soup.select('a[href*="/morphs/"]'):
            href = link.get('href', '')
            name = link.get_text(strip=True)
            if name and '/morphs/' in href:
                morphs.append({"name": name, "url": href if href.startswith('http') else 'https://www.worldofballpythons.com' + href, "species": "球蟒", "category": "snake", "source": "wobp"})
        seen = set()
        unique = []
        for m in morphs:
            if m['name'] not in seen:
                seen.add(m['name'])
                unique.append(m)
        print(f"  → {len(unique)} morphs (WOBP)", flush=True)
        return unique
    except Exception as e:
        print(f"  Error: {e}", flush=True)
        return []

print("=== MorphMarket + WOBP 基因爬取 ===", flush=True)
print(f"Start: {time.strftime('%H:%M:%S')}", flush=True)

targets = [
    ("https://www.morphmarket.com/morphs/", "球蟒", "snake"),
    ("https://www.morphmarket.com/morphs/?category=colubrids", "玉米蛇", "snake"),
    ("https://www.morphmarket.com/morphs/?category=geckos", "豹纹守宫", "lizard"),
    ("https://www.morphmarket.com/morphs/?category=hognose", "猪鼻蛇", "snake"),
    ("https://www.morphmarket.com/morphs/?category=boas", "红尾蚺", "snake"),
]

for url, name, cat in targets:
    results.extend(scrape_category(url, name, cat))
    time.sleep(3)

# WOBP for ball python depth
results.extend(scrape_wobp())

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({"scraped_at": time.strftime("%Y-%m-%d %H:%M"), "total": len(results), "morphs": results}, f, ensure_ascii=False, indent=2)

print(f"\nDone. {len(results)} morphs → {OUT}", flush=True)
