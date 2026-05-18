#!/usr/bin/env python3
"""将 B站训练帧打包为识龟模型训练数据集"""
import json, os, shutil, sqlite3, hashlib
from pathlib import Path

BILI_FRAMES = '/tmp/bili_frames'
OUTPUT_DIR = '/home/ubuntu/digeguigui/data/training/bili_v1'
DB_PATH = '/home/ubuntu/digeguigui/data/digeguigui.db'
MANIFEST_FILE = os.path.join(OUTPUT_DIR, 'manifest.json')

# 中文名 → species_id 映射
def build_cn_map(db):
    rows = db.execute("SELECT species_id, name_cn, name_latin FROM species WHERE name_cn IS NOT NULL").fetchall()
    cn_map = {}
    for sid, cn, latin in rows:
        cn_map[cn] = (sid, latin)
    return cn_map

# B站目录名 → 中文名映射（部分需要手动映射）
DIR_NAME_MAP = {
    '草龟': '草龟', '巴西龟': '巴西龟（密西西比红耳龟）', '剃刀龟': '剃刀龟',
    '麝香龟': '麝香龟', '地图龟': '地图龟', '鳄龟': '鳄龟',
    '猪鼻龟': '猪鼻龟', '黄缘': '黄缘闭壳龟', '黄喉': '黄喉拟水龟',
    '钻纹': '钻纹龟', '苏卡达': '苏卡达陆龟', '豹纹陆龟': '豹纹陆龟',
    '红腿': '红腿陆龟', '亚达': '亚达伯拉象龟', '东锦': '东锦龟',
    '西锦': '西锦龟', '箱龟': '箱龟', '木雕': '木雕水龟',
    '果核蛋龟': '果核泥龟', '巨头蛋龟': '巨头麝香龟', '白唇蛋龟': '白唇泥龟',
    '虎纹蛋龟': '虎纹麝香龟', '窄桥蛋龟': '鹰嘴泥龟', '萨尔文蛋龟': '萨尔文蛋龟',
    '墨西哥蛋龟': '墨西哥蛋龟', '平背': '平背麝香龟', '斑点池龟': '印度斑点水龟（hamiltonii）',
    '鹰嘴龟': '平胸龟', '枫叶龟': '枫叶龟', '金钱龟': '三线闭壳龟（金钱龟）',
}

def main():
    if not os.path.exists(BILI_FRAMES):
        print("❌ B站帧目录不存在")
        return
    
    db = sqlite3.connect(DB_PATH)
    cn_map = build_cn_map(db)
    
    # Show existing mappings
    for dir_name in DIR_NAME_MAP:
        cn = DIR_NAME_MAP[dir_name]
        if cn in cn_map:
            print(f"  {dir_name} → {cn} (#{cn_map[cn][0]})")
        else:
            # Try fuzzy match
            for db_cn, (sid, latin) in cn_map.items():
                if dir_name in db_cn or db_cn in dir_name:
                    print(f"  {dir_name} → {db_cn} (#{sid}) [fuzzy]")
                    DIR_NAME_MAP[dir_name] = db_cn
                    break
    
    # Clean and prepare output
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    manifest = {
        'version': '1.0',
        'source': 'bilibili',
        'created': os.popen('date -Iseconds').read().strip(),
        'species': {},
        'total_images': 0
    }
    
    # Walk through each species dir
    for dir_name in sorted(os.listdir(BILI_FRAMES)):
        dir_path = os.path.join(BILI_FRAMES, dir_name)
        if not os.path.isdir(dir_path):
            continue
        
        jpgs = []
        for root, dirs, files in os.walk(dir_path):
            for f in files:
                if f.endswith('.jpg'):
                    jpgs.append(os.path.join(root, f))
        if not jpgs:
            continue
        
        # Resolve species
        cn = DIR_NAME_MAP.get(dir_name, dir_name)
        match = cn_map.get(cn)
        if not match:
            # Fuzzy
            for db_cn, val in cn_map.items():
                if dir_name in db_cn or (cn and cn in db_cn):
                    match = val
                    cn = db_cn
                    break
        
        if not match:
            print(f"  ⚠️ {dir_name}: 无法匹配到 species，跳过 {len(jpgs)} 张")
            continue
        
        species_id, latin = match
        
        # Create output species dir
        out_species_dir = os.path.join(OUTPUT_DIR, f"{species_id:04d}_{latin.replace(' ', '_').replace('(', '').replace(')','').replace(',','')[:50]}")
        os.makedirs(out_species_dir, exist_ok=True)
        
        # Copy + hash-rename images
        copied = 0
        for jpg in jpgs:
            src = os.path.join(dir_path, jpg)
            # Hash content for unique filename
            with open(src, 'rb') as f:
                h = hashlib.md5(f.read()).hexdigest()[:12]
            dst = os.path.join(out_species_dir, f"{h}.jpg")
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                copied += 1
        
        manifest['species'][str(species_id)] = {
            'name_cn': cn,
            'name_latin': latin,
            'image_count': copied,
            'dir': os.path.basename(out_species_dir)
        }
        manifest['total_images'] += copied
        print(f"  ✅ {dir_name} → #{species_id} {latin}: {copied} images")
    
    # Write manifest
    with open(MANIFEST_FILE, 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    db.close()
    
    print(f"\n📦 Dataset packed: {OUTPUT_DIR}/")
    print(f"   Species: {len(manifest['species'])}")
    print(f"   Images: {manifest['total_images']}")
    print(f"   Manifest: {MANIFEST_FILE}")

if __name__ == '__main__':
    main()
