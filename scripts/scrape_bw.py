#!/usr/bin/env python3
"""
Backwater Reptiles 爬虫
产出: ~48种龟的产品数据 → JSON
"""

import json, re, time, sys, os
from urllib.request import urlopen, Request

BASE = "https://www.backwaterreptiles.com/"
UA = "Mozilla/5.0 (compatible; Digeguigui/1.0; +https://digeguigui.com)"
DELAY = 1.5
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "bw_products.json")

def fetch(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            req = Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
            req.add_header("Accept", "text/html,application/xhtml+xml")
            with urlopen(req, timeout=30) as resp:
                data = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    data = gzip.decompress(data)
                return data.decode("utf-8", errors="replace")
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  ⚠️ Failed: {url}: {e}", file=sys.stderr)
                return None
            time.sleep(3)
    return None

def extract_name(html, url):
    """Extract species name from title."""
    title = re.search(r'<title>([^<]+)</title>', html)
    if title:
        name = title.group(1)
        name = re.sub(r'\s*\|\s*Reptiles for Sale.*$', '', name).strip()
        name = re.sub(r'\s+for sale\s*$', '', name, flags=re.IGNORECASE).strip()
        return name
    return None

def extract_price(html):
    """Extract price from Backwater page."""
    # Backwater format: $39.99
    prices = re.findall(r'\$([\d,]+\.?\d*)', html)
    # First price is usually the product price (not shipping)
    for p in prices:
        val = float(p.replace(",", ""))
        if val < 1000 and val > 1:  # filter out shipping costs / weird amounts
            return val
    return None

def extract_image(html):
    """Extract main product image."""
    img = re.search(r'src="([^"]*/images/turtles/[^"]*\.(?:jpg|jpeg|png|webp))"', html)
    if img:
        return img.group(1)
    # Fallback: any turtle image
    img = re.search(r'src="([^"]*(?:turtle|musk|mud|map|slider|snapp|softshell|cooter|pond|sideneck|spotted|blanding|painted|box)[^"]*\.(?:jpg|jpeg|png|webp))"', html, re.IGNORECASE)
    return img.group(1) if img else None

def extract_description(html):
    """Extract product description."""
    # Main description paragraph
    desc = re.search(r'<p style="text-align:justify">(.*?)</p>', html, re.DOTALL)
    if desc:
        text = re.sub(r'<[^>]+>', '', desc.group(1)).strip()
        text = re.sub(r'\s+', ' ', text)
        return text
    
    # Fallback: first substantial paragraph
    paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
    for p in paras:
        text = re.sub(r'<[^>]+>', '', p).strip()
        text = re.sub(r'\s+', ' ', text)
        if len(text) > 40:
            return text
    return None

def extract_alt_names(html, name):
    """Extract 'also known as' names."""
    aka = re.search(r'also known as[:\s]*["\']?([^"\'\.]+)', html, re.IGNORECASE)
    if aka:
        return [n.strip() for n in aka.group(1).split(",")]
    
    # From description
    desc = extract_description(html) or ""
    aka_match = re.findall(r'also (?:known as|called)[:\s]+["\']?([^"\'\.]+)', desc, re.IGNORECASE)
    if aka_match:
        return [n.strip() for n in aka_match[0].split(",")]
    return []

def extract_size(html):
    """Extract size mention."""
    size = re.search(r'(?:maximum |adult )?size (?:of |is )?(?:approximately |approx\.? )?["\']?(\d+(?:\.\d+)?)[\s"\'"]*(?:inch|"|inches|cm)', html, re.IGNORECASE)
    if size:
        return size.group(0).strip()
    return None

def scrape_product(url):
    html = fetch(url)
    if not html:
        return None
    
    name = extract_name(html, url)
    price = extract_price(html)
    image = extract_image(html)
    description = extract_description(html)
    alt_names = extract_alt_names(html, name or "")
    size = extract_size(html)
    
    return {
        "url": url,
        "name": name,
        "price_usd": price,
        "image": image,
        "description": description,
        "alt_names": alt_names,
        "size_info": size,
    }

def discover_urls():
    """Discover all turtle product URLs from listing page."""
    html = fetch("https://www.backwaterreptiles.com/turtles-for-sale.html")
    if not html:
        return []
    
    urls = set()
    pattern = r'href="(https?://(?:www\.)?backwaterreptiles\.com/turtles/[^"]+\.html)"'
    matches = re.findall(pattern, html)
    for m in matches:
        # Filter out non-product pages
        if not any(skip in m.lower() for skip in ['supplies', 'accessories']):
            urls.add(m)
    
    # Also relative URLs
    rel = re.findall(r'href="(turtles/[^"]+\.html)"', html)
    for r in rel:
        url = f"https://www.backwaterreptiles.com/{r}"
        if not any(skip in r.lower() for skip in ['supplies', 'accessories']):
            urls.add(url)
    
    return sorted(urls)

def main():
    urls = discover_urls()
    print(f"🐢 Found {len(urls)} turtle products on Backwater Reptiles")
    
    products = []
    for i, url in enumerate(urls):
        short = url.split("/")[-1].replace("-for-sale.html", "").replace("-", " ")
        print(f"  [{i+1}/{len(urls)}] {short[:50]}")
        
        prod = scrape_product(url)
        if prod:
            products.append(prod)
            print(f"    ✅ {prod['name'][:50]} | ${prod['price_usd']} | img={bool(prod['image'])}")
        else:
            print(f"    ❌ Failed")
        
        if i < len(urls) - 1:
            time.sleep(DELAY)
    
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    with_prices = sum(1 for p in products if p["price_usd"])
    with_images = sum(1 for p in products if p["image"])
    print(f"\n✅ {OUTPUT}: {len(products)} products | {with_prices} with prices | {with_images} with images")

if __name__ == "__main__":
    main()
