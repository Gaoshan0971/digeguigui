#!/usr/bin/env python3
"""
SnakesAtSunset 龟类产品爬虫
URL自带拉丁学名 + BigCommerce平台 → 匹配零成本
"""

import json, re, time, sys, os
from urllib.request import urlopen, Request

UA = "Mozilla/5.0 (compatible; Digeguigui/1.0)"
BASE = "https://snakesatsunset.com/"
DELAY = 1.5
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "sas_products.json")

def fetch(url):
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
            with urlopen(req, timeout=30) as resp:
                data = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    data = gzip.decompress(data)
                return data.decode("utf-8", errors="replace")
        except Exception as e:
            if attempt == 2:
                print(f"  ⚠️ {url}: {e}")
                return None
            time.sleep(3)
    return None

def discover_urls():
    """从列表页发现所有龟类产品URL"""
    html = fetch("https://www.snakesatsunset.com/turtles-for-sale/")
    if not html:
        return []
    
    urls = set()
    urls.update(re.findall(r'href="(https://snakesatsunset\.com/[^"]*(?:turtle|tortoise|slider|map|mud|musk|snapping|softshell|cooter|pond|sideneck|spotted|blanding|painted|box|terrapin)[^"]*)"', html, re.IGNORECASE))
    
    # 去重（去#product-reviews等锚点）
    clean_urls = set()
    for u in urls:
        u = u.split('#')[0].rstrip('/') + '/'
        clean_urls.add(u)
    
    return sorted(clean_urls)

def extract_latin_name(url):
    """从URL提取拉丁学名"""
    # Pattern: ...-for-sale-emydura-subglobosa-2022/
    slug = url.rstrip('/').split('/')[-1]
    
    # 尝试匹配已知模式
    patterns = [
        r'-(trachemys-scripta-\w+)',
        r'-(chelydra-serpentina)',
        r'-(emydura-subglobosa)',
        r'-(kinostern[ou][mn]-\w+)',
        r'-(sternotherus-\w+)',
        r'-(graptemys-\w+)',
        r'-(pseudemys-\w+)',
        r'-(terrapene-\w+)',
        r'-(testudo-\w+)',
        r'-(chelodina-\w+)',
        r'-(pelusios-\w+)',
        r'-(cuora-\w+)',
        r'-(mauremys-\w+)',
        r'-(chelus-\w+)',
        r'-(apalone-\w+)',
        r'-(clemmys-\w+)',
        r'-(emydoidea-\w+)',
        r'-(glyptemys-\w+)',
        r'-(malaclemys-\w+)',
        r'-(deirochelys-\w+)',
        r'-(chrysemys-\w+)',
        r'-(centrochelys-\w+)',
        r'-(stigmochelys-\w+)',
        r'-(chelonoidis-\w+)',
        r'-(aldabrachelys-\w+)',
        r'-(indotestudo-\w+)',
    ]
    
    for pat in patterns:
        m = re.search(pat, url, re.IGNORECASE)
        if m:
            # 转回标准格式: trachemys-scripta-elegans → Trachemys scripta elegans
            latin = m.group(0).lstrip('-').replace('-', ' ')
            # Capitalize genus
            parts = latin.split()
            if parts:
                parts[0] = parts[0].capitalize()
            return ' '.join(parts)
    
    return None

def extract_name(html):
    title = re.search(r'<title>([^<]+)</title>', html)
    if title:
        name = title.group(1)
        name = re.sub(r'\s*\|\s*Snakes at Sunset.*$', '', name).strip()
        name = re.sub(r'\s+for sale\s*$', '', name, flags=re.IGNORECASE).strip()
        return name
    return None

def extract_price(html):
    """BigCommerce JSON-LD or embedded price"""
    # JSON-LD
    prices = re.findall(r'"price":\s*([\d.]+)', html)
    if prices:
        return float(prices[0])
    
    # Embedded data
    m = re.search(r'"without_tax":\s*\{[^}]*"value":\s*([\d.]+)', html)
    if m:
        return float(m.group(1))
    
    # Dollar amounts
    m = re.findall(r'\$([\d,]+\.?\d*)', html)
    for p in m:
        val = float(p.replace(',', ''))
        if val > 1 and val < 10000:
            return val
    
    return None

def extract_images(html):
    """BigCommerce CDN product images"""
    images = []
    pattern = r'src="(https://cdn11\.bigcommerce\.com/s-g64jf8ws/images/stencil/(?:500x659|1280x1280|original)/products/\d+/\d+/[^"]+\.(?:jpg|jpeg|png|webp))"'
    for img in re.findall(pattern, html, re.IGNORECASE):
        images.append(img)
    
    if not images:
        pattern = r'src="(https://cdn11\.bigcommerce\.com/[^"]*500x659[^"]*\.(?:jpg|jpeg|png|webp))"'
        images = re.findall(pattern, html, re.IGNORECASE)
    
    return list(dict.fromkeys(images))

def extract_description(html):
    """Product description"""
    meta = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
    if meta:
        return meta.group(1)
    
    paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
    for p in paras:
        text = re.sub(r'<[^>]+>', '', p).strip()
        text = re.sub(r'\s+', ' ', text)
        if len(text) > 50:
            return text
    return None

def detect_morph(name, html):
    """Detect morph/variant from name and description"""
    morph_tags = []
    morph_keywords = ['albino', 'hypo', 'leucistic', 'melanistic', 'paradox', 'translucent',
                      'axanthic', 'caramel', 'ghost', 'snow', 'piebald', 'pastel', 'charcoal',
                      'platinum', 'heterozygous', 'het', 't-positive', 't-',
                      'golden', 'flame', 'emerald', 'imperfect', 'perfect']
    name_lower = (name or '').lower()
    for kw in morph_keywords:
        if kw in name_lower:
            morph_tags.append(kw)
    return morph_tags

def scrape_product(url):
    html = fetch(url)
    if not html:
        return None
    
    name = extract_name(html)
    latin = extract_latin_name(url)
    price = extract_price(html)
    images = extract_images(html)
    description = extract_description(html)
    morph_tags = detect_morph(name, html)
    
    return {
        "url": url,
        "name": name,
        "latin": latin,
        "price_usd": price,
        "images": images,
        "description": description,
        "morph_tags": morph_tags,
    }

def main():
    urls = discover_urls()
    print(f"🐢 Found {len(urls)} turtle products on SnakesAtSunset")
    
    products = []
    for i, url in enumerate(urls):
        short = url.split('/')[-2][:50]
        print(f"  [{i+1}/{len(urls)}] {short}")
        
        prod = scrape_product(url)
        if prod:
            products.append(prod)
            lat = prod['latin'] or '?'
            price = f"${prod['price_usd']}" if prod['price_usd'] else '?'
            imgs = len(prod['images'])
            morphs = ','.join(prod['morph_tags']) if prod['morph_tags'] else '-'
            print(f"    ✅ {lat[:30]} | {price} | {imgs}imgs | {morphs}")
        else:
            print(f"    ❌ Failed")
        
        if i < len(urls) - 1:
            time.sleep(DELAY)
    
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    with_prices = sum(1 for p in products if p['price_usd'])
    with_latin = sum(1 for p in products if p['latin'])
    with_morph = sum(1 for p in products if p['morph_tags'])
    print(f"\n✅ {OUTPUT}: {len(products)} products | {with_latin} with latin | {with_prices} with prices | {with_morph} with morphs")

if __name__ == '__main__':
    main()
