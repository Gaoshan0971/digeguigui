#!/usr/bin/env python3
"""异宠全量批量爬取：从候选名单读取，复用三源爬虫"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

import importlib.util
spec = importlib.util.spec_from_file_location("scrape_v3",
    os.path.join(os.path.dirname(__file__), "scrape_species_v3.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Load candidates
with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'exotics_candidates.json')) as f:
    candidates = json.load(f)

# Filter to full species only (skip subspecies: 3-part names where 3rd is lowercase)
filtered = []
for c in candidates:
    parts = c['name_latin'].split()
    if len(parts) >= 3 and parts[2][0].islower() and parts[0][0].isupper():
        # subspecies — use parent species instead
        parent = f"{parts[0]} {parts[1]}"
        # Check if parent already in list
        if not any(x['name_latin'] == parent for x in filtered):
            filtered.append({"name_cn": c['name_cn'], "name_latin": parent})
    else:
        filtered.append(c)

print(f"📋 爬取目标: {len(filtered)} 种 (过滤亚种后)")

mod.SPECIES = [(c['name_cn'], c['name_latin']) for c in filtered]
mod.DELAY = 0.5  # 0.5s delay between species
mod.OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'species_exotics_full.json')

mod.main()
