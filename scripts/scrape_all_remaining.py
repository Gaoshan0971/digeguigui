#!/usr/bin/env python3
"""全量龟类爬取：从缺失列表读取，批量三源采集"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util

spec = importlib.util.spec_from_file_location("scrape_v3", 
    os.path.join(os.path.dirname(__file__), "scrape_species_v3.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Read missing species
with open('/tmp/turtle_missing.txt') as f:
    missing = [l.strip() for l in f if l.strip()]

# Generate Chinese names from Latin (simple fallback)
mod.SPECIES = [(s, s) for s in missing]  # Use Latin as both CN and EN name

# Reduce delay for bulk run
mod.DELAY = 1
mod.OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'species_full.json')

mod.main()
