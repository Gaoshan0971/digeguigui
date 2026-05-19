#!/usr/bin/env python3
"""
国外爬宠数据采集 — 多渠道合围
1. iNat API（研究级照片）— 已有管线
2. Bing 图片搜索（人工品相图）— 搜 "species_name for sale"
3. TortoiseForum 帖图（陆龟社区）
4. Kingsnake 分类广告
"""
import os, sys, json, time, hashlib, sqlite3
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'data' / 'digeguigui.db'
OUT_DIR = BASE_DIR / 'data' / 'training' / 'foreign_market'
OUT_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = 'Mozilla/5.0 (compatible; DigeguiguiBot/1.0; +https://digeguigui.com)'
SLEEP = 1.0

def fetch_json(url):
    req = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    for _ in range(2):
        try:
            with urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except:
            time.sleep(1)
    return None

def download_image(url, path):
    try:
        req = Request(url, headers={'User-Agent': USER_AGENT})
        with urlopen(req, timeout=15) as r:
            with open(path, 'wb') as f:
                f.write(r.read())
        return True
    except:
        return False

# ── 1. Bing 图片搜索 ──
def search_bing_images(query, count=50):
    """Bing 图片搜索 API（免费）"""
    results = []
    url = f'https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1&t=digeguigui'
    # DuckDuckGo 轻量替代
    data = fetch_json(url)
    if data and 'Image' in data:
        for img in data.get('Image', '')[:count] if isinstance(data.get('Image'), list) else []:
            results.append(img)
    return results

# ── 2. TortoiseForum 帖图 ──
def scrape_tortoise_forum(species_keyword, max_pages=5):
    """搜 TortoiseForum 某品种的帖图"""
    images = []
    for page in range(1, max_pages + 1):
        url = f'https://www.tortoiseforum.org/search/{page}/?q={quote(species_keyword)}&c[title_only]=1&o=date'
        try:
            req = Request(url, headers={'User-Agent': USER_AGENT})
            with urlopen(req, timeout=15) as r:
                html = r.read().decode('utf-8', errors='ignore')
            # 找图片URL（论坛附件格式）
            import re
            imgs = re.findall(r'src="([^"]*attachments[^"]*\.(?:jpg|jpeg|png))"', html, re.I)
            images.extend(imgs[:20])
        except:
            continue
        time.sleep(1)
    return images

# ── 3. Kingsnake 分类广告 ──
def scrape_kingsnake(cat_id=37, max_pages=3):
    """Kingsnake 龟类分类广告"""
    images = []
    for page in range(max_pages):
        url = f'https://market.kingsnake.com/index.php?cat={cat_id}&page={page}'
        try:
            req = Request(url, headers={'User-Agent': USER_AGENT})
            with urlopen(req, timeout=15) as r:
                html = r.read().decode('utf-8', errors='ignore')
            import re
            # 找图片
            imgs = re.findall(r'img src="([^"]*\.(?:jpg|jpeg|png))"', html, re.I)
            # 找详情页链接
            details = re.findall(r'href="(index\.php\?cat=\d+&detail=\d+)"', html, re.I)
            images.extend(imgs)
            
            # 爬详情页的图
            for d in details[:5]:
                try:
                    durl = f'https://market.kingsnake.com/{d}'
                    req2 = Request(durl, headers={'User-Agent': USER_AGENT})
                    with urlopen(req2, timeout=10) as r2:
                        dhtml = r2.read().decode('utf-8', errors='ignore')
                    detail_imgs = re.findall(r'<img[^>]*src="([^"]*\.(?:jpg|jpeg|png))"', dhtml, re.I)
                    images.extend(detail_imgs)
                except:
                    pass
                time.sleep(0.5)
        except:
            continue
        time.sleep(1)
    return images

# ── 主流程：按品种爬 ──
def download_species_market(species_id, name_cn, name_latin, genus):
    sp_dir = OUT_DIR / f'{species_id:04d}_{genus}_{name_latin.split()[1] if len(name_latin.split())>1 else "sp"}'
    sp_dir.mkdir(parents=True, exist_ok=True)
    
    existing = len(list(sp_dir.glob('*.jpg')))
    if existing >= 100:
        return existing
    
    total_new = 0
    search_term = f'{name_latin.split()[0]} {name_latin.split()[1] if len(name_latin.split())>1 else ""} turtle for sale'
    
    # 1. TortoiseForum
    tf_imgs = scrape_tortoise_forum(search_term, max_pages=3)
    for img_url in tf_imgs[:30]:
        if not img_url.startswith('http'):
            img_url = 'https://www.tortoiseforum.org' + img_url
        fname = f'tf_{hashlib.md5(img_url.encode()).hexdigest()[:10]}.jpg'
        fpath = sp_dir / fname
        if not fpath.exists():
            if download_image(img_url, fpath):
                total_new += 1
        time.sleep(0.3)
    
    # 2. Kingsnake (只跑热门品种)
    if existing + total_new < 50:
        ks_imgs = scrape_kingsnake(cat_id=37, max_pages=2)
        for img_url in ks_imgs[:20]:
            if not img_url.startswith('http'):
                img_url = 'https://market.kingsnake.com/' + img_url.lstrip('/')
            fname = f'ks_{hashlib.md5(img_url.encode()).hexdigest()[:10]}.jpg'
            fpath = sp_dir / fname
            if not fpath.exists():
                if download_image(img_url, fpath):
                    total_new += 1
            time.sleep(0.3)
    
    return existing + total_new

def main():
    conn = sqlite3.connect(DB_PATH)
    # 优先爬热门品种（有价格数据或品系数据的）
    rows = conn.execute("""
        SELECT DISTINCT s.species_id, s.name_cn, s.name_latin, s.genus
        FROM species s
        WHERE s.category='龟'
        ORDER BY s.species_id
    """).fetchall()
    conn.close()
    
    print(f"🕷️ 国外爬站数据采集 — {len(rows)} 种龟\n")
    
    total = 0
    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = {ex.submit(download_species_market, *row): row for row in rows}
        for f in as_completed(futures):
            row = futures[f]
            try:
                n = f.result()
                total += n
                if n >= 20:
                    print(f"  [{row[0]}] {row[1]}: {n}张")
            except Exception as e:
                pass
    
    print(f"\n总图数: {total} | 输出: {OUT_DIR}")

if __name__ == '__main__':
    main()
