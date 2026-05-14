#!/usr/bin/env python3
"""batch_scrape.py — 分批爬取 + 合并"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location("v3", os.path.join(os.path.dirname(__file__), "scrape_species_v3.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if len(sys.argv) < 2:
    print("Usage: python3 batch_scrape.py <batch_index>")
    print("  Reads exotics_candidates.json, scrapes batch N (50 per batch)")
    sys.exit(1)

batch_idx = int(sys.argv[1])
BATCH_SIZE = 55

with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'exotics_candidates.json')) as f:
    candidates = json.load(f)

filtered = []
for c in candidates:
    parts = c['name_latin'].split()
    if len(parts) >= 3 and parts[2][0].islower() and parts[0][0].isupper():
        parent = f"{parts[0]} {parts[1]}"
        if not any(x['name_latin'] == parent for x in filtered):
            filtered.append({"name_cn": c['name_cn'], "name_latin": parent})
    else:
        filtered.append(c)

total = len(filtered)
batches = [filtered[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]

if batch_idx >= len(batches):
    print(f"Batch {batch_idx} out of range (0-{len(batches)-1})")
    sys.exit(1)

batch = batches[batch_idx]
outfile = os.path.join(os.path.dirname(__file__), '..', 'data', f'species_exotics_batch_{batch_idx}.json')

print(f"📦 Batch {batch_idx}/{len(batches)-1}: {len(batch)} species → {outfile}")

mod.DELAY = 0.2
mod.SPECIES = [(c['name_cn'], c['name_latin']) for c in batch]
mod.OUTPUT_FILE = outfile
mod.main()
