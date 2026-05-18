#!/usr/bin/env python3
"""从 SAS 产品页提取并下载高清产品图片"""
import json, re, os, time, urllib.request, hashlib

SAS_FILE = '/home/ubuntu/digeguigui/data/sas_products.json'
IMG_DIR = '/home/ubuntu/digeguigui/data/sas_images'
os.makedirs(IMG_DIR, exist_ok=True)

with open(SAS_FILE) as f:
    products = json.load(f)

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def fetch_page(url, retries=2):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if attempt == retries - 1:
                return None
            time.sleep(2)

def extract_images(html, url):
    """Extract full-size product images from BigCommerce HTML"""
    images = set()
    
    # Pattern 1: stencil/1280x1280/products/{pid}/{iid}/{file} (full size)
    for m in re.finditer(r'https?://[^"\s]+/images/stencil/(?:1280x1280|original)/products/\d+/\d+/[^"\s]+\.(?:jpg|jpeg|png|webp)', html):
        img = m.group(0).split('?')[0]  # Remove query params
        if 'logo' not in img.lower() and 'favacon' not in img.lower():
            images.add(img)
    
    # Pattern 2: products/{pid}/images/{iid}/{file} (upload original, no stencil)
    # These are smaller but sometimes the only version
    if not images:
        for m in re.finditer(r'https?://[^"\s]+/products/\d+/images/\d+/[^"\s]+\.(?:jpg|jpeg|png|webp)', html):
            img = m.group(0).split('?')[0]
            if 'logo' not in img.lower() and 'favacon' not in img.lower() and '220.220' not in img:
                images.add(img)
    
    # Pattern 3: data-src or srcset with full-size img
    if not images:
        for m in re.finditer(r'(?:data-src|data-zoom-image)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)', html):
            img = m.group(1).split('?')[0]
            if 'logo' not in img.lower():
                images.add(img)
    
    return list(images)

total_new = 0
for i, prod in enumerate(products):
    if prod.get('images') and len(prod['images']) > 0:
        continue  # Already has images
    
    latin = prod.get('latin', '?')
    url = prod.get('url', '')
    
    print(f"[{i+1}/{len(products)}] {latin[:30]}...", end=' ')
    
    html = fetch_page(url)
    if not html:
        print("❌ fetch fail")
        continue
    
    imgs = extract_images(html, url)
    if not imgs:
        print("❌ no images")
        continue
    
    # Download first image as primary
    img_url = imgs[0]
    ext = img_url.split('.')[-1].split('?')[0]
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', latin)[:40]
    fname = f"{safe_name}_{hashlib.md5(img_url.encode()).hexdigest()[:8]}.{ext}"
    fpath = os.path.join(IMG_DIR, fname)
    
    try:
        req = urllib.request.Request(img_url, headers={'User-Agent': UA, 'Referer': url})
        with urllib.request.urlopen(req, timeout=20) as resp:
            with open(fpath, 'wb') as f:
                f.write(resp.read())
        prod['images'] = [img_url]  # Store all URLs
        total_new += 1
        print(f"✅ {len(imgs)} imgs → {fname}")
    except Exception as e:
        print(f"❌ download fail: {e}")
    
    time.sleep(0.3)  # Rate limit

# Save updated
with open(SAS_FILE, 'w') as f:
    json.dump(products, f, indent=2, ensure_ascii=False)

print(f"\n✅ Downloaded {total_new} new product images → {IMG_DIR}/")
print(f"Total products with images: {sum(1 for p in products if p.get('images') and len(p['images'])>0)}/{len(products)}")
