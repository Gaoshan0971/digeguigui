#!/usr/bin/env python3
"""
TheTurtleSource.com 爬虫
产出: 产品数据 + care sheets + morph信息 → JSON → 可导入滴个龟龟DB
"""

import json, re, time, sys, os
from urllib.request import urlopen, Request
from urllib.parse import urljoin
from html.parser import HTMLParser

BASE = "https://theturtlesource.com/"
UA = "Mozilla/5.0 (compatible; Digeguigui/1.0; +https://digeguigui.com)"
DELAY = 2  # seconds between requests
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "tts_products.json")
CARE_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "tts_care_sheets.json")

def fetch(url, max_retries=3):
    """Fetch URL with retry and return decoded HTML text."""
    for attempt in range(max_retries):
        try:
            req = Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
            req.add_header("Accept", "text/html,application/xhtml+xml")
            with urlopen(req, timeout=30) as resp:
                data = resp.read()
                # Handle gzip
                if resp.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    data = gzip.decompress(data)
                return data.decode("utf-8", errors="replace")
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  ⚠️ Failed to fetch {url}: {e}", file=sys.stderr)
                return None
            time.sleep(3)
    return None

def extract_jsonld(html):
    """Extract product JSON-LD from BigCommerce product page."""
    pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL)
    for m in matches:
        try:
            data = json.loads(m)
            if data.get("@type") == "Product":
                return data
        except json.JSONDecodeError:
            continue
    return None

def extract_price(html):
    """Extract price from JSON-LD or BigCommerce price data."""
    # Method 1: BigCommerce price JSON in script
    pattern = r'"price_without_tax":\s*\{[^}]*"value":\s*([\d.]+)'
    m = re.search(pattern, html)
    if m:
        return float(m.group(1))
    
    # Method 2: dollar amount
    pattern = r'\$([\d,]+\.?\d*)'
    prices = re.findall(pattern, html)
    if prices:
        return float(prices[0].replace(",", ""))
    
    return None

def extract_price_range(html):
    """Extract price range from BigCommerce variants."""
    # Look for price_range in embedded data
    pattern = r'"price_range":\s*\{[^}]*"min":\s*\{[^}]*"without_tax":\s*\{[^}]*"value":\s*([\d.]+)[^}]*"max":\s*\{[^}]*"without_tax":\s*\{[^}]*"value":\s*([\d.]+)'
    m = re.search(pattern, html, re.DOTALL)
    if m:
        return {"min": float(m.group(1)), "max": float(m.group(2))}
    
    price = extract_price(html)
    if price:
        return {"min": price, "max": price}
    return None

def extract_images(html, base_url):
    """Extract product image URLs."""
    images = []
    # BigCommerce product images - stencil path pattern
    # Main images: /images/stencil/558x558/products/ID/filename.jpg
    # Thumbnails: /images/stencil/90x90/products/ID/filename.jpg
    # Also: /images/stencil/original/... (logo etc)
    pattern = r'src="(https://cdn11\.bigcommerce\.com/s-skdyft6w8e/images/stencil/(?:558x558|1280x1280|original)/products/\d+/\d+/[^"]+\.(?:jpg|jpeg|png|webp)(?:\?c=\d+)?)"'
    matches = re.findall(pattern, html, re.IGNORECASE)
    
    # Deduplicate and strip query params
    seen = set()
    for img in matches:
        clean = re.sub(r'\?c=\d+$', '', img)
        if clean not in seen:
            seen.add(clean)
            images.append(clean)
    
    if not images:
        # Fallback: any 558x558 product image
        pattern = r'src="(https://cdn11\.bigcommerce\.com/[^"]*558x558[^"]*\.(?:jpg|jpeg|png|webp)(?:\?c=\d+)?)"'
        for img in re.findall(pattern, html, re.IGNORECASE):
            clean = re.sub(r'\?c=\d+$', '', img)
            if clean not in seen:
                seen.add(clean)
                images.append(clean)
    
    return images

def extract_description(html):
    """Extract product description paragraphs."""
    # Meta description
    meta = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
    meta_text = meta.group(1) if meta else ""
    
    # Product description paragraphs (in productView-description area)
    paragraphs = []
    # Find the description block
    desc_pattern = r'(?:<div[^>]*class="[^"]*productView-description[^"]*"[^>]*>|<div[^>]*id="product-description[^"]*"[^>]*>)(.*?)(?:</div>\s*<(?:div|/div|section))'
    desc_match = re.search(desc_pattern, html, re.DOTALL)
    
    if desc_match:
        desc_html = desc_match.group(1)
        # Extract text from <p> tags
        paras = re.findall(r'<p[^>]*>(.*?)</p>', desc_html, re.DOTALL)
        for p in paras:
            text = re.sub(r'<[^>]+>', '', p).strip()
            text = re.sub(r'\s+', ' ', text)
            if len(text) > 30:
                paragraphs.append(text)
    
    if not paragraphs:
        # Fallback: any substantial paragraph on the page
        all_paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
        for p in all_paras:
            text = re.sub(r'<[^>]+>', '', p).strip()
            text = re.sub(r'\s+', ' ', text)
            if len(text) > 50 and not any(skip in text.lower() for skip in ['order by', 'encrypted site', 'business hour', 'copyright', 'all rights reserved']):
                paragraphs.append(text)
    
    return paragraphs

def extract_name(html):
    """Extract product name from title or h1."""
    title = re.search(r'<title>([^<]+)</title>', html)
    if title:
        name = title.group(1)
        # Clean up common suffixes
        name = re.sub(r'\s*[-|]\s*The Turtle Source.*$', '', name).strip()
        name = re.sub(r'\s*[-|]\s*Turtles for Sale.*$', '', name).strip()
        name = re.sub(r'\s*[-|]\s*Tortoises for Sale.*$', '', name).strip()
        name = re.sub(r'\s+for sale\s*$', '', name, flags=re.IGNORECASE).strip()
        return name
    
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html)
    if h1:
        return re.sub(r'<[^>]+>', '', h1.group(1)).strip()
    return None

def extract_category(html, url):
    """Guess category from breadcrumbs or URL."""
    # Breadcrumbs
    bc = re.findall(r'<li[^>]*class="[^"]*breadcrumb[^"]*"[^>]*>.*?<span[^>]*>(.*?)</span>', html, re.DOTALL)
    for item in bc:
        text = re.sub(r'<[^>]+>', '', item).strip()
        if text.lower() in ['turtles', 'tortoises', 'water turtles', 'box turtles', 'wood turtles', 'garden pond turtles', 'side-necks', 'morphs']:
            return text
    
    # From URL pattern
    if '/tortoise' in url.lower():
        return 'Tortoises'
    if any(x in url.lower() for x in ['/turtle', 'mud-', 'musk-', 'map-', 'slider', 'snapping', 'softshell', 'cooter', 'pond', 'sideneck', 'spotted', 'blanding', 'painted', 'chicken', 'diamondback']):
        return 'Turtles'
    return 'Other'

def extract_morph_tags(name, url):
    """Detect morph/genetics tags from product name."""
    morphs = []
    morph_keywords = ['albino', 'hypo', 'leucistic', 'melanistic', 'paradox', 'translucent',
                      'axanthic', 'caramel', 'ghost', 'snow', 'piebald', 'pastel', 'charcoal',
                      'platinum', 'heterozygous', 'het', 't-positive', 't+', 't-',
                      'golden', 'flame', 'emerald', 'patternless', 'hybrid']
    name_lower = name.lower()
    for kw in morph_keywords:
        if kw in name_lower:
            morphs.append(kw)
    return morphs

def scrape_product(url):
    """Scrape a single product page."""
    print(f"  📦 {url}")
    html = fetch(url)
    if not html:
        return None
    
    name = extract_name(html)
    price_range = extract_price_range(html)
    images = extract_images(html, url)
    description = extract_description(html)
    category = extract_category(html, url)
    morph_tags = extract_morph_tags(name or "", url)
    
    # Extract structured JSON-LD for richer data
    jsonld = extract_jsonld(html)
    
    return {
        "url": url,
        "name": name,
        "price": price_range,
        "images": images,
        "description": description,
        "category": category,
        "morph_tags": morph_tags,
        "jsonld_name": jsonld.get("name") if jsonld else None,
        "jsonld_description": jsonld.get("description") if jsonld else None,
        "jsonld_sku": jsonld.get("sku") if jsonld else None,
        "jsonld_brand": jsonld.get("brand", {}).get("name") if jsonld else None,
    }

def scrape_care_sheet(url):
    """Scrape a care sheet page."""
    print(f"  📋 {url}")
    html = fetch(url)
    if not html:
        return None
    
    title = re.search(r'<h1[^>]*>(.*?)</h1>', html)
    title = re.sub(r'<[^>]+>', '', title.group(1)).strip() if title else url.split("/")[-2].replace("-", " ").title()
    
    # Extract all content sections
    sections = []
    # Find headings and their content
    content_pattern = r'<(?:h[12]|strong|b)[^>]*>(.*?)</(?:h[12]|strong|b)>\s*<p[^>]*>(.*?)</p>'
    matches = re.findall(content_pattern, html, re.DOTALL)
    for heading, content in matches:
        h_text = re.sub(r'<[^>]+>', '', heading).strip()
        c_text = re.sub(r'<[^>]+>', '', content).strip()
        c_text = re.sub(r'\s+', ' ', c_text)
        if len(c_text) > 30:
            sections.append({"heading": h_text, "content": c_text})
    
    # Also get body paragraphs
    body_paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
    body_text = []
    for p in body_paras:
        text = re.sub(r'<[^>]+>', '', p).strip()
        text = re.sub(r'\s+', ' ', text)
        if len(text) > 50 and not any(skip in text.lower() for skip in ['order by 12pm', 'encrypted site', 'business hour', 'copyright']):
            body_text.append(text)
    
    return {
        "url": url,
        "title": title,
        "sections": sections,
        "body": body_text[:20]  # first 20 meaningful paragraphs
    }

def main():
    # Product URLs
    product_urls = [
        "https://theturtlesource.com/albino-pink-belly-side-necked-turtle/",
        "https://theturtlesource.com/aldabra-tortoise/",
        "https://theturtlesource.com/asian-yellow-pond-turtle/",
        "https://theturtlesource.com/black-wood-turtle/",
        "https://theturtlesource.com/bolivian-cherry-headed-red-footed-tortoise/",
        "https://theturtlesource.com/charcoal-red-eared-slider/",
        "https://theturtlesource.com/charcoal-red-eared-slider-garden-pond-sizes/",
        "https://theturtlesource.com/chinese-golden-box-turtle/",
        "https://theturtlesource.com/cohilan-box-turtle/",
        "https://theturtlesource.com/common-snapping-turtle/",
        "https://theturtlesource.com/elongated-tortoise/",
        "https://theturtlesource.com/emerald-albino-paradox-red-eared-slider/",
        "https://theturtlesource.com/emerald-albino-paradox-red-eared-slider-garden-pond-sizes/",
        "https://theturtlesource.com/florida-chicken-turtle/",
        "https://theturtlesource.com/furrowed-wood-turtle/",
        "https://theturtlesource.com/giant-asian-leaf-pond-turtle-heosemys-grandis/",
        "https://theturtlesource.com/gibba-side-necked-turtle-mesoclemmys-gibba/",
        "https://theturtlesource.com/golden-flame-florida-red-bellied-turtle-garden-pond-sizes/",
        "https://theturtlesource.com/greek-tortoise/",
        "https://theturtlesource.com/hermanns-tortoise/",
        "https://theturtlesource.com/hybrid-rio-grande-red-eared-mexican-ornate-garden-pond-sizes/",
        "https://theturtlesource.com/hypo-melanistic-common-snapping-turtle/",
        "https://theturtlesource.com/hypo-translucent-albino-red-eared-slider/",
        "https://theturtlesource.com/japanese-wood-turtle/",
        "https://theturtlesource.com/kwangtung-river-turtle-garden-pond-sizes/",
        "https://theturtlesource.com/leopard-tortoise/",
        "https://theturtlesource.com/leucistic-albino-red-eared-slider/",
        "https://theturtlesource.com/madagascar-big-headed-side-necked-turtles/",
        "https://theturtlesource.com/maracaibo-wood-turtle/",
        "https://theturtlesource.com/melanistic-red-eared-slider/",
        "https://theturtlesource.com/mexican-red-wood-turtle/",
        "https://theturtlesource.com/north-american-wood-turtle/",
        "https://theturtlesource.com/painted-river-terrapin/",
        "https://theturtlesource.com/painted-river-terrapin-garden-pond-sizes/",
        "https://theturtlesource.com/painted-wood-turtle/",
        "https://theturtlesource.com/paradox-albino/",
        "https://theturtlesource.com/paradox-albino-red-eared-slider-garden-pond-sizes/",
        "https://theturtlesource.com/patterened-sulcata-tortoises/",
        "https://theturtlesource.com/platinum-yellow-leucistic-red-foot-tortoise/",
        "https://theturtlesource.com/red-eared-slider-heterozygous-for-albino/",
        "https://theturtlesource.com/red-footed-tortoise/",
        "https://theturtlesource.com/ringed-map-turtle/",
        "https://theturtlesource.com/southern-river-cooter-garden-pond-sizes/",
        "https://theturtlesource.com/sulcata-tortoise/",
        "https://theturtlesource.com/sulcata-tortoise-adult/",
        "https://theturtlesource.com/three-striped-mud-turtle/",
        "https://theturtlesource.com/t-positive-albino-florida-red-belly/",
        "https://theturtlesource.com/white-lipped-mud-turtle/",
        "https://theturtlesource.com/yellow-bellied-sliders-heterozygous-for-albino/",
        "https://theturtlesource.com/yellow-blotched-map-turtle/",
    ]
    
    care_sheet_urls = [
        "https://theturtlesource.com/blandings-turtle-care-sheet/",
        "https://theturtlesource.com/box-turtle-care-sheet/",
        "https://theturtlesource.com/chicken-turtle-care-sheet/",
        "https://theturtlesource.com/diamondback-terrapin-care-sheet/",
        "https://theturtlesource.com/map-turtle-care-sheet/",
        "https://theturtlesource.com/matamata-turtle-care-sheet/",
        "https://theturtlesource.com/mud-and-musk-turtle-care-sheet/",
        "https://theturtlesource.com/painted-turtle-care-sheet/",
        "https://theturtlesource.com/slider-and-cooter-care-sheet/",
        "https://theturtlesource.com/snapping-turtle-care-sheet/",
        "https://theturtlesource.com/soft-shelled-turtle-care-sheet/",
        "https://theturtlesource.com/spotted-wood-bog-and-western-pond-turtle-care-sheet/",
        "https://theturtlesource.com/vietnamese-pond-turtle-care-sheet/",
        "https://theturtlesource.com/juvenile-tortoise-care-sheet/",
        "https://theturtlesource.com/leopard-tortoise-care-sheet/",
        "https://theturtlesource.com/red-yellow-footed-tortoise-care-sheet/",
        "https://theturtlesource.com/salcata-and-african-spurred-toirtoise-care-sheet/",
    ]
    
    print(f"🦎 Scraping {len(product_urls)} products from TheTurtleSource...")
    products = []
    for i, url in enumerate(product_urls):
        prod = scrape_product(url)
        if prod:
            products.append(prod)
            print(f"    ✅ {prod['name'][:60]} | ${prod['price']} | {len(prod['images'])} images | morphs: {prod['morph_tags']}")
        else:
            print(f"    ❌ Failed")
        
        if i < len(product_urls) - 1:
            time.sleep(DELAY)
    
    print(f"\n📋 Scraping {len(care_sheet_urls)} care sheets...")
    care_sheets = []
    for i, url in enumerate(care_sheet_urls):
        sheet = scrape_care_sheet(url)
        if sheet:
            care_sheets.append(sheet)
            print(f"    ✅ {sheet['title'][:60]} | {len(sheet['sections'])} sections | {len(sheet['body'])} paragraphs")
        else:
            print(f"    ❌ Failed")
        
        if i < len(care_sheet_urls) - 1:
            time.sleep(DELAY)
    
    # Save
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Products saved: {OUTPUT} ({len(products)} items)")
    
    with open(CARE_OUTPUT, "w") as f:
        json.dump(care_sheets, f, ensure_ascii=False, indent=2)
    print(f"✅ Care sheets saved: {CARE_OUTPUT} ({len(care_sheets)} items)")
    
    # Summary
    total_images = sum(len(p["images"]) for p in products)
    with_prices = sum(1 for p in products if p["price"])
    with_morphs = sum(1 for p in products if p["morph_tags"])
    print(f"\n📊 Summary: {len(products)} products | {total_images} images | {with_prices} with prices | {with_morphs} with morph tags | {len(care_sheets)} care sheets")

if __name__ == "__main__":
    main()
