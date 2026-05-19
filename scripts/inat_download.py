#!/usr/bin/env python3
"""
iNat 全量龟类训练图下载
从 iNaturalist 拉取研究级 CC 协议龟类照片，按品种归档
输出: data/training/inat_v2/{species_id}_{genus}_{species}/

用法:
  python scripts/inat_download.py                    # 全量368种
  python scripts/inat_download.py --species 57 68 74  # 指定品种
  python scripts/inat_download.py --min-images 50 --max-images 500  # 每品种图数
"""
import os, sys, json, time, sqlite3, argparse, hashlib
from pathlib import Path
from urllib.request import urlopen, Request, urlretrieve
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'data' / 'digeguigui.db'
OUT_DIR = BASE_DIR / 'data' / 'training' / 'inat_v2'
CACHE_DIR = BASE_DIR / 'data' / 'cache' / 'inat_taxon'
OUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = 'Digeguigui/1.0 (research project; contact@digeguigui.com)'
SLEEP = 0.7  # iNat 限制 ~100 req/min，保守 85/min

def api_get(url):
    """iNat API 调用，带重试（快速失败策略）"""
    req = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    for attempt in range(2):
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt == 1:
                return None
            time.sleep(1)

def search_taxon(scientific_name):
    """搜索 iNat taxon_id（去掉作者年份），缓存避免重复调用"""
    # 去掉括号和作者年份: "Sternotherus carinatus (Gray, 1856)" → "Sternotherus carinatus"
    clean = scientific_name.split('(')[0].split(',')[0].strip()
    cache_key = hashlib.md5(clean.encode()).hexdigest()[:12]
    cache_file = CACHE_DIR / f'{cache_key}.json'
    
    if cache_file.exists():
        with open(cache_file) as f:
            cached = json.load(f)
            if cached.get('taxon_id'):
                return cached['taxon_id']
            else:
                return None  # 已搜过，失败，直接跳过
    
    time.sleep(SLEEP)
    data = api_get(f'https://api.inaturalist.org/v1/taxa?q={quote(clean)}&rank=species&per_page=5')
    if not data or not data.get('results'):
        with open(cache_file, 'w') as f:
            json.dump({'taxon_id': None, 'name': clean}, f)  # 缓存失败
        return None
    
    # 精确匹配学名（忽略大小写）
    for r in data['results']:
        if r.get('name', '').lower() == clean.lower():
            taxon_id = r['id']
            with open(cache_file, 'w') as f:
                json.dump({'taxon_id': taxon_id, 'name': clean}, f)
            return taxon_id
    
    # 退一步：取第一个结果
    taxon_id = data['results'][0]['id']
    with open(cache_file, 'w') as f:
        json.dump({'taxon_id': taxon_id, 'name': clean, 'fuzzy': True}, f)
    return taxon_id

def download_species_photos(species_id, scientific_name, chinese_name, 
                             min_images=50, max_images=500):
    """下载单个品种的 iNat 照片"""
    taxon_id = search_taxon(scientific_name)
    if not taxon_id:
        print(f"  [{species_id}] {chinese_name} ({scientific_name[:40]}): ❌ 未找到 iNat taxon")
        return 0
    
    # 创建品种目录
    safe_genus = scientific_name.split()[0]
    safe_species = scientific_name.split()[1] if len(scientific_name.split()) > 1 else 'sp'
    dirname = f'{species_id:04d}_{safe_genus}_{safe_species}'.replace('(', '').replace(')', '').replace(',', '')
    sp_dir = OUT_DIR / dirname
    sp_dir.mkdir(parents=True, exist_ok=True)
    
    # 已有多少张？
    existing = list(sp_dir.glob('*.jpg'))
    if len(existing) >= max_images:
        print(f"  [{species_id}] {chinese_name}: ✅ 已有{len(existing)}张，跳过")
        return len(existing)
    
    downloaded = len(existing)
    page = 1
    
    while downloaded < max_images:
        url = (f'https://api.inaturalist.org/v1/observations'
               f'?taxon_id={taxon_id}'
               f'&quality_grade=research'
               f'&photo_license=cc0,cc-by,cc-by-sa'
               f'&per_page=200&page={page}'
               f'&order=desc&order_by=created_at')
        
        time.sleep(SLEEP)
        data = api_get(url)
        if not data or not data.get('results'):
            break
        
        for obs in data['results']:
            if downloaded >= max_images:
                break
            photos = obs.get('observation_photos', []) or obs.get('photos', [])
            for p in photos:
                if downloaded >= max_images:
                    break
                # iNat photo URL结构: square/medium/large/original
                if isinstance(p, dict):
                    photo = p.get('photo', p)
                else:
                    photo = p
                img_url = photo.get('url', '').replace('square', 'large')
                if not img_url:
                    continue
                
                obs_id = obs['id']
                photo_id = photo.get('id', 'unknown')
                fname = f'{obs_id}_{photo_id}.jpg'
                fpath = sp_dir / fname
                
                if fpath.exists():
                    continue
                
                try:
                    time.sleep(0.1)  # 下载间隔
                    req = Request(img_url, headers={'User-Agent': USER_AGENT})
                    with urlopen(req, timeout=15) as resp:
                        with open(fpath, 'wb') as out:
                            out.write(resp.read())
                    downloaded += 1
                    if downloaded % 20 == 0:
                        print(f"  [{species_id}] {chinese_name}: {downloaded}张...", end='\r')
                except Exception as e:
                    continue
        
        page += 1
        # 最后一页数据不够一页说明完了
        if len(data['results']) < 200:
            break
    
    print(f"  [{species_id}] {chinese_name}: ✅ {downloaded}张 (需≥{min_images})")
    return downloaded

def main():
    parser = argparse.ArgumentParser(description='iNat 龟类训练图下载')
    parser.add_argument('--min-images', type=int, default=100, help='每品种最少图数')
    parser.add_argument('--max-images', type=int, default=500, help='每品种最多图数')
    parser.add_argument('--species', type=int, nargs='*', help='指定品种ID（默认全部368种）')
    parser.add_argument('--workers', type=int, default=3, help='并发数（注意API限速）')
    args = parser.parse_args()
    
    # 从DB读品种列表
    conn = sqlite3.connect(DB_PATH)
    if args.species:
        placeholders = ','.join('?' * len(args.species))
        rows = conn.execute(
            f"SELECT species_id, name_latin, name_cn FROM species WHERE species_id IN ({placeholders})",
            args.species
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT species_id, name_latin, name_cn FROM species WHERE category='龟' ORDER BY species_id"
        ).fetchall()
    conn.close()
    
    print(f"📸 iNat 龟类图下载 — {len(rows)}种")
    print(f"   每品种 {args.min_images}~{args.max_images}张 | 并发 {args.workers} | 输出 {OUT_DIR}")
    print(f"   预计 {(len(rows) * (args.max_images//200 + 1) * SLEEP / args.workers / 60):.0f} 分钟\n")
    
    total = 0
    success = 0
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                download_species_photos, 
                row[0], row[1], row[2],
                args.min_images, args.max_images
            ): row for row in rows
        }
        for f in as_completed(futures):
            row = futures[f]
            try:
                n = f.result()
                total += n
                if n >= args.min_images:
                    success += 1
            except Exception as e:
                print(f"  [{row[0]}] {row[2]}: ❌ {e}")
    
    print(f"\n{'='*50}")
    print(f"完成: {success}/{len(rows)}种达标 ≥{args.min_images}张")
    print(f"总图数: {total}")
    print(f"输出目录: {OUT_DIR}")

if __name__ == '__main__':
    main()
