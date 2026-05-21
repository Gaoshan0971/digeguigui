"""
scrape_training_images.py — 从 iNaturalist 批量抓取龟类训练图
目标：56品种 × 20-50张 = 1000-2800张训练集
来源：iNaturalist observations (CC 授权实拍，多角度/多环境)
"""

import requests
import json
import time
import os
import sys
from pathlib import Path

API = 'https://api.inaturalist.org/v1'
HEADERS = {
    'User-Agent': 'Digeguigui/1.0',
    'Referer': 'https://www.inaturalist.org'
}
OUT_DIR = Path('/tmp/turtle_dataset')
REQ_INTERVAL = 2.0  # API 限速
TARGET_PER_SPECIES = 50
OBS_PER_PAGE = 100

# 56 品种（拉丁学名）
SPECIES = [
    ("红耳龟", "Trachemys scripta elegans"),
    ("黄喉拟水龟", "Mauremys mutica"),
    ("中华草龟", "Mauremys reevesii"),
    ("中华花龟", "Mauremys sinensis"),
    ("黄缘闭壳龟", "Cuora flavomarginata"),
    ("黄额闭壳龟", "Cuora galbinifrons"),
    ("三线闭壳龟", "Cuora trifasciata"),
    ("安布闭壳龟", "Cuora amboinensis"),
    ("东部箱龟", "Terrapene carolina carolina"),
    ("锦箱龟", "Terrapene ornata"),
    ("剃刀龟", "Sternotherus carinatus"),
    ("麝香龟", "Sternotherus odoratus"),
    ("巨头麝香龟", "Sternotherus minor"),
    ("平背麝香龟", "Sternotherus depressus"),
    ("果核泥龟", "Kinosternon baurii"),
    ("黄泥龟", "Kinosternon flavescens"),
    ("红面泥龟", "Kinosternon scorpioides cruentatum"),
    ("白唇泥龟", "Kinosternon leucostomum"),
    ("窄桥麝香龟", "Claudius angustatus"),
    ("大麝香龟", "Staurotypus triporcatus"),
    ("萨尔文麝香龟", "Staurotypus salvinii"),
    ("鳄龟", "Chelydra serpentina"),
    ("大鳄龟", "Macrochelys temminckii"),
    ("苏卡达陆龟", "Centrochelys sulcata"),
    ("豹纹陆龟", "Stigmochelys pardalis"),
    ("红腿陆龟", "Chelonoidis carbonarius"),
    ("黄腿陆龟", "Chelonoidis denticulatus"),
    ("赫曼陆龟", "Testudo hermanni"),
    ("希腊陆龟", "Testudo graeca"),
    ("四爪陆龟", "Testudo horsfieldii"),
    ("辐射陆龟", "Astrochelys radiata"),
    ("安哥洛卡陆龟", "Astrochelys yniphora"),
    ("亚达伯拉象龟", "Aldabrachelys gigantea"),
    ("缅甸陆龟", "Indotestudo elongata"),
    ("印度星龟", "Geochelone elegans"),
    ("缅甸星龟", "Geochelone platynota"),
    ("饼干陆龟", "Malacochersus tornieri"),
    ("钻纹龟", "Malaclemys terrapin"),
    ("地图龟", "Graptemys geographica"),
    ("拟地图龟", "Graptemys pseudogeographica"),
    ("甜甜圈龟", "Pseudemys concinna"),
    ("西部锦龟", "Chrysemys picta bellii"),
    ("东部锦龟", "Chrysemys picta picta"),
    ("猪鼻龟", "Carettochelys insculpta"),
    ("棱皮龟", "Dermochelys coriacea"),
    ("斑点池龟", "Geoclemys hamiltonii"),
    ("木雕水龟", "Glyptemys insculpta"),
    ("星点水龟", "Clemmys guttata"),
    ("黑瘤地图龟", "Graptemys nigrinoda"),
    ("阿拉巴马地图龟", "Graptemys pulchra"),
    ("佛罗里达鳖", "Apalone ferox"),
    ("中华鳖", "Pelodiscus sinensis"),
    ("圆澳龟", "Emydura subglobosa"),
    ("枯叶龟", "Chelus fimbriata"),
    ("希拉里蟾头龟", "Phrynops hilarii"),
    ("黄头侧颈龟", "Podocnemis unifilis"),
]

def get_taxon_id(scientific_name):
    """搜索 taxon ID"""
    resp = requests.get(f'{API}/taxa', params={'q': scientific_name, 'rank': 'species'}, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    results = resp.json().get('results', [])
    for r in results:
        if r.get('rank') == 'species':
            return r['id']
    if results:
        return results[0]['id']
    return None

def get_observations(taxon_id, page=1):
    """获取观察记录（含图片）"""
    resp = requests.get(f'{API}/observations', params={
        'taxon_id': taxon_id,
        'per_page': OBS_PER_PAGE,
        'page': page,
        'order': 'desc',
        'quality_grade': 'research',
        'photos': 'true',
        'photo_license': 'cc-by,cc-by-nc,cc-by-sa,cc0'
    }, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()

def download_image(url, path):
    """下载单张图"""
    try:
        resp = requests.get(url.replace('square', 'medium'), headers=HEADERS, timeout=15)
        if resp.status_code == 200 and len(resp.content) > 1000:
            path.write_bytes(resp.content)
            return True
    except:
        pass
    return False

def scrape_species(name_cn, scientific_name):
    """爬单个品种"""
    species_dir = OUT_DIR / name_cn
    species_dir.mkdir(parents=True, exist_ok=True)

    # 已有多少
    existing = list(species_dir.glob('*.jpg'))
    if len(existing) >= TARGET_PER_SPECIES:
        return {'name': name_cn, 'new': 0, 'total': len(existing), 'status': 'done'}

    print(f'  🔍 {name_cn} ({scientific_name})')

    taxon_id = get_taxon_id(scientific_name)
    if not taxon_id:
        print(f'    ❌ 未找到 taxon')
        return {'name': name_cn, 'new': 0, 'total': len(existing), 'status': 'no_taxon'}

    downloaded = 0
    page = 1
    while downloaded + len(existing) < TARGET_PER_SPECIES and page <= 10:
        try:
            data = get_observations(taxon_id, page)
        except Exception as e:
            print(f'    ⚠️ 第{page}页失败: {e}')
            break

        results = data.get('results', [])
        if not results:
            break

        for obs in results:
            photos = obs.get('photos', [])
            observer = obs.get('user', {}).get('login', 'unknown')
            obs_id = obs['id']

            for idx, photo in enumerate(photos):
                if downloaded + len(existing) >= TARGET_PER_SPECIES:
                    break

                url = photo.get('url', '')
                if not url:
                    continue

                filename = f'{obs_id}_{idx}.jpg'
                filepath = species_dir / filename

                if filepath.exists():
                    continue

                if download_image(url, filepath):
                    downloaded += 1
                    # 保存 attribution
                    meta_path = species_dir / f'{obs_id}_{idx}.json'
                    meta_path.write_text(json.dumps({
                        'observer': observer,
                        'license': photo.get('license_code', ''),
                        'attribution': photo.get('attribution', ''),
                        'inat_url': f'https://www.inaturalist.org/observations/{obs_id}',
                        'url': url
                    }, ensure_ascii=False), encoding='utf-8')

            if downloaded + len(existing) >= TARGET_PER_SPECIES:
                break

        page += 1
        time.sleep(REQ_INTERVAL)

    total = len(existing) + downloaded
    print(f'    {"✅" if total >= TARGET_PER_SPECIES else "⏳"} {total}张 (+{downloaded})')
    return {'name': name_cn, 'new': downloaded, 'total': total, 'status': 'done' if total >= TARGET_PER_SPECIES else 'partial'}

def main():
    print(f'🐢 滴个龟龟 — iNaturalist 训练图采集')
    print(f'   目标: {TARGET_PER_SPECIES}张/种 × {len(SPECIES)}种')
    print(f'   输出: {OUT_DIR}')
    print()

    results = []
    start = time.time()

    for name_cn, latin in SPECIES:
        r = scrape_species(name_cn, latin)
        results.append(r)
        if r['name'] != SPECIES[-1][0]:
            time.sleep(REQ_INTERVAL)

    # 汇总
    total_new = sum(r['new'] for r in results)
    total_all = sum(r['total'] for r in results)
    done = sum(1 for r in results if r['status'] == 'done')
    partial = sum(1 for r in results if r['status'] == 'partial')
    failed = sum(1 for r in results if r['status'] == 'no_taxon')

    print(f'\n{"="*50}')
    print(f'📊 采集完成 ({time.time()-start:.0f}s)')
    print(f'   新增: {total_new} 张')
    print(f'   总计: {total_all} 张')
    print(f'   达标(≥{TARGET_PER_SPECIES}): {done}/{len(SPECIES)}')
    print(f'   部分: {partial} | 未找到: {failed}')
    print(f'   目录: {OUT_DIR}')

    # 生成训练清单
    manifest = []
    for r in results:
        species_dir = OUT_DIR / r['name']
        imgs = list(species_dir.glob('*.jpg'))
        manifest.append({'name_cn': r['name'], 'count': len(imgs), 'images': [str(p) for p in imgs]})

    manifest_path = OUT_DIR / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'   清单: {manifest_path}')

if __name__ == '__main__':
    main()
