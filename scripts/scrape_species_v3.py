#!/usr/bin/env python3
"""
scrape_species_v3.py — 三源权威数据采集（GBIF + iNaturalist + Reptile Database）
用法: /usr/bin/python3 scripts/scrape_species_v3.py
"""
import requests
import json
import time
import sys
import os
import re

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'species_authoritative.json')
DELAY = 2
UA = 'Digeguigui/1.0 (digeguigui.com; research project)'

SPECIES = [
    ("剃刀龟", "Sternotherus carinatus"),
    ("麝香龟", "Sternotherus odoratus"),
    ("巨头麝香龟", "Sternotherus minor"),
    ("平背麝香龟", "Sternotherus depressus"),
    ("白唇泥龟", "Kinosternon leucostomum"),
    ("红面泥龟", "Kinosternon scorpioides cruentatum"),
    ("黄泽泥龟", "Kinosternon subrubrum"),
    ("果核泥龟", "Kinosternon baurii"),
    ("牟氏水龟", "Glyptemys muhlenbergii"),
    ("鹰嘴泥龟", "Claudius angustatus"),
]


def gbif_taxonomy(scientific_name):
    """GBIF: 权威分类学"""
    try:
        resp = requests.get("https://api.gbif.org/v1/species/match",
                          params={"name": scientific_name},
                          headers={"User-Agent": UA}, timeout=15)
        if resp.status_code == 200:
            d = resp.json()
            if d.get("confidence", 0) >= 90:
                return {
                    "scientific_name": d.get("scientificName"),
                    "family": d.get("family"),
                    "genus": d.get("genus"),
                    "class": d.get("class"),
                    "order": d.get("order"),
                    "kingdom": d.get("kingdom"),
                }
    except Exception as e:
        print(f"  ⚠️ GBIF: {e}", file=sys.stderr)
    return None


def inat_species(session, scientific_name):
    """iNaturalist: 通用名 + CC 图片 + Wiki"""
    try:
        resp = session.get("https://api.inaturalist.org/v1/taxa",
                          params={"q": scientific_name, "rank": "species", "per_page": 1},
                          headers={"User-Agent": UA, "Referer": "https://www.inaturalist.org"},
                          timeout=15)
        if resp.status_code != 200:
            return None
        results = resp.json().get("results", [])
        if not results:
            return None
        r = results[0]
        photo = r.get("default_photo", {})
        return {
            "common_name": r.get("preferred_common_name"),
            "wikipedia_url": r.get("wikipedia_url"),
            "observations_count": r.get("observations_count", 0),
            "conservation": r.get("conservation_status", {}).get("status_name"),
            "image_url": photo.get("medium_url") if photo else None,
            "image_attribution": photo.get("attribution", "") if photo else None,
            "image_license": photo.get("license_code", "") if photo else None,
        }
    except Exception as e:
        print(f"  ⚠️ iNat: {e}", file=sys.stderr)
    return None


def reptiledb_species(scientific_name):
    """Reptile Database: 分布 + 栖息地 + 繁殖 + 命名由来 + 同义名"""
    genus, species = scientific_name.split(" ", 1)
    url = f"https://reptile-database.reptarium.cz/species?genus={genus}&species={species}"
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=15, allow_redirects=True)
        if resp.status_code != 200:
            return None
        html = resp.text

        # 清理 HTML 取纯文本
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '\n', text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)

        data = {}

        # 分布
        m = re.search(r'Distribution\s*\n+(.*?)(?:\n{2,}|\n(?:Type locality|Reproduction|Habitat|Diagnosis|Comment|Common Names))', text, re.DOTALL)
        if m:
            data['distribution'] = m.group(1).strip().replace('\n', ' ')[:300]

        # 模式产地
        m = re.search(r'Type locality:\s*(.*?)(?:\n|$)', text)
        if m:
            data['type_locality'] = m.group(1).strip()[:200]

        # 栖息地
        m = re.search(r'Habitat:\s*(.*?)(?:\n|$)', text)
        if m:
            data['habitat'] = m.group(1).strip()[:200]

        # 繁殖
        if 'oviparous' in text.lower():
            data['reproduction'] = 'oviparous'
            m = re.search(r'oviparous[^.]*\.', text, re.IGNORECASE)
            if m:
                data['reproduction_detail'] = m.group(0).strip()[:200]

        # 命名由来
        m = re.search(r'Named after\s*(.*?)(?:\n|\.|$)', text)
        if m:
            data['etymology'] = m.group(1).strip()[:200]

        # 多语言通用名（从 Common Names 段）
        common_block = re.search(r'Common Names\n(.*?)(?:\n\n|\n[A-Z][a-z])', text, re.DOTALL)
        if common_block:
            names = common_block.group(1).strip().split('\n')
            data['common_names_all'] = [n.strip() for n in names if n.strip() and len(n.strip()) > 3][:10]

        # 同义名
        syn_lines = []
        for line in text.split('\n'):
            line = line.strip()
            if re.match(r'^[A-Z][a-z]+.*\d{4}', line) and len(line) > 20:
                syn_lines.append(line)
        if syn_lines:
            data['synonyms'] = syn_lines[:15]

        return data if data else None

    except Exception as e:
        print(f"  ⚠️ ReptileDB: {e}", file=sys.stderr)
    return None


def merge(name_cn, sci_name, gbif, inat, repdb):
    """三源合并"""
    result = {
        "name_cn": name_cn,
        "name_latin": gbif.get("scientific_name") if gbif else sci_name,
        "common_name_en": None,
        "family": None,
        "genus": None,
        "class": None,
        "distribution": None,
        "habitat": None,
        "type_locality": None,
        "conservation": None,
        "reproduction": None,
        "etymology": None,
        "image_url": None,
        "image_attribution": None,
        "image_license": None,
        "wikipedia_url": None,
        "observations_count": 0,
        "common_names_all": [],
        "synonyms": [],
        "difficulty": None,
        "price_range": None,
        "traits": {},
        "care_params": {},
        "sources": {"gbif": bool(gbif), "inat": bool(inat), "repdb": bool(repdb)},
    }

    if gbif:
        for k in ["scientific_name", "family", "genus", "class", "order", "kingdom"]:
            if gbif.get(k):
                result[k if k != "scientific_name" else "name_latin"] = gbif[k]
        result["name_latin"] = gbif.get("scientific_name")

    if inat:
        for k in ["common_name", "wikipedia_url", "observations_count",
                   "conservation", "image_url", "image_attribution", "image_license"]:
            if inat.get(k):
                result[k if k != "common_name" else "common_name_en"] = inat[k]
        result["common_name_en"] = inat.get("common_name")

    if repdb:
        for k in ["distribution", "habitat", "type_locality", "reproduction",
                   "reproduction_detail", "etymology", "common_names_all", "synonyms"]:
            if repdb.get(k):
                result[k] = repdb[k]
        # 繁殖信息提炼
        if repdb.get("reproduction_detail"):
            result["reproduction"] = repdb["reproduction_detail"]

    # 置信度
    score = 0
    if result["name_latin"]: score += 15
    if result["family"]: score += 15
    if result["genus"]: score += 10
    if result["distribution"]: score += 20
    if result["habitat"]: score += 15
    if result["image_url"]: score += 15
    if result["wikipedia_url"]: score += 5
    if result["conservation"]: score += 5
    result["_confidence"] = score

    return result


def main():
    session = requests.Session()
    results = []

    print(f"🐢 三源采集：GBIF + iNaturalist + Reptile Database")
    print(f"   {len(SPECIES)} 个蛋龟品种\n")

    for i, (name_cn, sci_name) in enumerate(SPECIES, 1):
        print(f"[{i}/{len(SPECIES)}] {name_cn} ({sci_name}) ...", end=' ', flush=True)

        gbif = gbif_taxonomy(sci_name)
        gbif_ok = "✅" if gbif else "❌"

        time.sleep(0.5)
        inat = inat_species(session, sci_name)
        inat_ok = "✅" if inat else "❌"

        time.sleep(0.5)
        repdb = reptiledb_species(sci_name)
        repdb_ok = "✅" if repdb else "❌"

        species = merge(name_cn, sci_name, gbif, inat, repdb)
        results.append(species)

        dist = species.get("distribution", "?")[:40] if species.get("distribution") else "?"
        print(f"GBIF:{gbif_ok} iNat:{inat_ok} RDB:{repdb_ok} | 分布:{dist} | {species['_confidence']}%")

        if i < len(SPECIES):
            time.sleep(DELAY)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    avg = sum(r["_confidence"] for r in results) / len(results)
    w_dist = sum(1 for r in results if r["distribution"])
    w_habitat = sum(1 for r in results if r["habitat"])
    w_etym = sum(1 for r in results if r["etymology"])

    print(f"\n{'='*55}")
    print(f"📄 {OUTPUT_FILE}")
    print(f"   平均置信度: {avg:.0f}% | 有分布: {w_dist} | 有栖息地: {w_habitat} | 有命名: {w_etym}")
    print(f"   数据源: GBIF + iNaturalist (CC) + Reptile Database")

if __name__ == '__main__':
    main()
