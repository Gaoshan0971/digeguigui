#!/usr/bin/env python3
"""merge_and_import.py — 合并分批爬取结果 + 直接入仓"""
import json, os, sqlite3, sys

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
DB_PATH = os.path.join(DATA_DIR, 'digeguigui.db')

# Merge batch files
all_species = []
for f in sorted(os.listdir(DATA_DIR)):
    if not f.startswith('species_exotics_batch_') or not f.endswith('.json'):
        continue
    fp = os.path.join(DATA_DIR, f)
    with open(fp) as fh:
        batch = json.load(fh)
    all_species.extend(batch)
    print(f"  {f}: {len(batch)} species")

# Include species_exotics_full.json (main from scrape_all_exotics.py)
full_file = os.path.join(DATA_DIR, 'species_exotics_full.json')
if os.path.exists(full_file):
    with open(full_file) as fh:
        full_data = json.load(fh)
    print(f"  species_exotics_full.json: {len(full_data)} records")
    all_species.extend(full_data)

# Also include the first batch from species_authoritative.json
auth_file = os.path.join(DATA_DIR, 'species_authoritative.json')
if os.path.exists(auth_file):
    with open(auth_file) as fh:
        auth_data = json.load(fh)
    new = [s for s in auth_data if s.get('class') != 'Testudines' and 'turtle' not in s.get('family','').lower()]
    if new:
        print(f"  species_authoritative.json: {len(new)} additional exotics")
        all_species.extend(new)

# Also include species_exotics.json (first 35)
exo_file = os.path.join(DATA_DIR, 'species_exotics.json')
if os.path.exists(exo_file):
    with open(exo_file) as fh:
        exo_data = json.load(fh)
    print(f"  species_exotics.json: {len(exo_data)} records")
    all_species.extend(exo_data)

# Deduplicate by latin name
seen = set()
deduped = []
for s in all_species:
    key = s['name_latin'].strip().lower()
    if key and key not in seen:
        seen.add(key)
        deduped.append(s)

print(f"\n✅ 合并去重后: {len(deduped)} 种异宠")

# Save merged
merged_file = os.path.join(DATA_DIR, 'species_exotics_merged.json')
with open(merged_file, 'w') as f:
    json.dump(deduped, f, ensure_ascii=False, indent=2)
print(f"💾 {merged_file}")

# Import to SQLite
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Ensure columns exist
for col, typ in [('category','TEXT'),('class_name','TEXT')]:
    try: cur.execute(f"ALTER TABLE species ADD COLUMN {col} {typ} DEFAULT ''")
    except: pass

# Classification helper
def classify(s):
    cls = (s.get('class','') or '').lower()
    fam = (s.get('family','') or '').lower()
    if 'testudines' in cls: return '龟'
    if 'amphibia' in cls: return '蛙'
    if not cls or 'squamata' in cls:
        gecko_fams = ['eublepharidae','diplodactylidae','gekkonidae','pygopodidae','sphaerodactylidae']
        snake_fams = ['colubridae','pythonidae','boidae','viperidae','elapidae','tropidophiidae','xenopeltidae']
        if any(f in fam for f in gecko_fams): return '守宫'
        if any(f in fam for f in snake_fams): return '蛇'
        if fam: return '蜥蜴'
    return '其他'

inserted = 0
updated = 0

for s in deduped:
    if s.get('error'): continue
    cat = classify(s)
    latin = s['name_latin'].strip()
    
    existing = cur.execute("SELECT species_id FROM species WHERE name_latin=?", (latin,)).fetchone()
    
    cur.execute("""
        INSERT INTO species (
            name_cn, name_latin, common_name_en, family, genus,
            distribution, habitat, conservation, reproduction, etymology,
            image_url, image_attribution, image_license,
            wikipedia_url, observations_count,
            category, class_name
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(name_latin) DO UPDATE SET
            name_cn=excluded.name_cn,
            common_name_en=COALESCE(excluded.common_name_en, species.common_name_en),
            family=COALESCE(excluded.family, species.family),
            genus=COALESCE(excluded.genus, species.genus),
            distribution=COALESCE(excluded.distribution, species.distribution),
            habitat=COALESCE(excluded.habitat, species.habitat),
            conservation=COALESCE(excluded.conservation, species.conservation),
            reproduction=COALESCE(excluded.reproduction, species.reproduction),
            etymology=COALESCE(excluded.etymology, species.etymology),
            image_url=COALESCE(excluded.image_url, species.image_url),
            image_attribution=COALESCE(excluded.image_attribution, species.image_attribution),
            image_license=COALESCE(excluded.image_license, species.image_license),
            wikipedia_url=COALESCE(excluded.wikipedia_url, species.wikipedia_url),
            observations_count=COALESCE(excluded.observations_count, species.observations_count),
            category=COALESCE(excluded.category, species.category),
            class_name=COALESCE(excluded.class_name, species.class_name)
    """, (
        s['name_cn'], latin, s.get('common_name_en',''),
        s.get('family',''), s.get('genus',''),
        s.get('distribution',''), s.get('habitat',''),
        s.get('conservation',''), s.get('reproduction',''),
        s.get('etymology',''), s.get('image_url',''),
        s.get('image_attribution',''), s.get('image_license',''),
        s.get('wikipedia_url',''), s.get('observations_count',0),
        cat, s.get('class','')
    ))
    
    if existing: updated += 1
    else: inserted += 1

conn.commit()

# Final stats
cur.execute("SELECT category, COUNT(*) FROM species GROUP BY category ORDER BY COUNT(*) DESC")
print(f"\n📊 基因库:")
for cat, cnt in cur.fetchall():
    print(f"  {cat}: {cnt} 种")
print(f"  ──────────")
cur.execute("SELECT COUNT(*) FROM species")
print(f"  总计: {cur.fetchone()[0]} 种")
print(f"  新增: {inserted} | 更新: {updated}")

conn.close()
