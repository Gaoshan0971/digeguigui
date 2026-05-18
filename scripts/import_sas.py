#!/usr/bin/env python3
"""导入 SnakesAtSunset 爬虫数据到滴个龟龟 DB"""
import json, sqlite3, sys, os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'digeguigui.db')
SAS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'sas_products.json')

def main():
    if not os.path.exists(SAS_FILE):
        print("❌ sas_products.json not found")
        sys.exit(1)
    
    products = json.load(open(SAS_FILE))
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    
    # Prepare statements
    # Try exact Latin name match first, then fuzzy
    exact_match = db.execute("SELECT name_latin FROM species").fetchall()
    db_latins = {r['name_latin'].lower().strip(): r['name_latin'] for r in exact_match if r['name_latin']}
    
    matched = 0
    unmatched = []
    updated = 0
    morph_linked = 0
    
    for prod in products:
        latin = prod.get('latin', '').strip()
        if not latin:
            unmatched.append(prod)
            continue
        
        # Try exact match
        latin_lower = latin.lower()
        db_latin = db_latins.get(latin_lower)
        
        # Try fuzzy if no exact match
        if not db_latin:
            # Try matching genus+species parts
            parts = latin_lower.split()
            for db_key, db_val in db_latins.items():
                db_parts = db_key.split()
                if len(parts) >= 2 and len(db_parts) >= 2:
                    if parts[0] == db_parts[0] and parts[1] == db_parts[1]:
                        db_latin = db_val
                        break
        
        # Try LIKE match
        if not db_latin:
            row = db.execute(
                "SELECT name_latin FROM species WHERE name_latin LIKE ? LIMIT 1",
                (f"%{latin.split()[0]}%{latin.split()[-1]}%" if ' ' in latin else f"%{latin}%",)
            ).fetchone()
            if row:
                db_latin = row['name_latin']
        
        if not db_latin:
            unmatched.append(prod)
            continue
        
        matched += 1
        
        # Build market data to insert
        price = prod.get('price_usd')
        url = prod.get('url', '')
        images = prod.get('images', [])
        morph_tags = prod.get('morph_tags', [])
        
        # Get existing market_data
        row = db.execute("SELECT market_data FROM species WHERE name_latin = ?", (db_latin,)).fetchone()
        if not row:
            continue
        
        existing = json.loads(row['market_data'] or '{}')
        
        # Add SAS entry
        existing['sas_url'] = url
        existing['sas_price'] = price
        
        # Track morph info
        if morph_tags:
            existing['sas_morph'] = morph_tags
            morph_linked += 1
        
        # Update market_range from all sources
        prices = []
        for key in ['tts_price', 'bw_price', 'sas_price']:
            if existing.get(key) and isinstance(existing[key], (int, float)):
                prices.append(existing[key])
        if prices:
            existing['price_min'] = min(prices)
            existing['price_max'] = max(prices)
        
        # Update species
        db.execute(
            "UPDATE species SET market_data = ? WHERE name_latin = ?",
            (json.dumps(existing), db_latin)
        )
        updated += 1
    
    db.commit()
    db.close()
    
    print(f"✅ SAS 导入完成:")
    print(f"   匹配入库: {matched}")
    print(f"   品系关联: {morph_linked}")
    print(f"   未匹配: {len(unmatched)}")
    
    if unmatched:
        print(f"\n未匹配品种:")
        for p in unmatched:
            print(f"   {p.get('latin','?')} — {p.get('name','')[:40]} — ${p.get('price_usd','?')}")

if __name__ == '__main__':
    main()
