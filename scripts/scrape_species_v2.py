#!/usr/bin/env python3
"""
scrape_species_v2.py — 权威数据源爬虫（GBIF + iNaturalist）
用法: /usr/bin/python3 scripts/scrape_species_v2.py
"""
import requests
import json
import time
import sys
import os

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'species_authoritative.json')
DELAY = 2  # 请求间隔，尊重 API
UA = 'Digeguigui/1.0 (digeguigui.com; research project)'

# 10 个蛋龟品种（拉丁学名）
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
    """从 GBIF 获取权威分类学信息"""
    url = "https://api.gbif.org/v1/species/match"
    try:
        resp = requests.get(url, params={"name": scientific_name},
                          headers={"User-Agent": UA}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("confidence", 0) >= 90:
                return {
                    "scientific_name": data.get("scientificName"),
                    "canonical_name": data.get("canonicalName"),
                    "kingdom": data.get("kingdom"),
                    "phylum": data.get("phylum"),
                    "class": data.get("class"),
                    "order": data.get("order"),
                    "family": data.get("family"),
                    "genus": data.get("genus"),
                    "species": data.get("species"),
                    "rank": data.get("rank"),
                    "match_type": data.get("matchType"),
                    "confidence": data.get("confidence"),
                }
    except Exception as e:
        print(f"  ⚠️ GBIF error: {e}", file=sys.stderr)
    return None


def resolve_ancestors(session, ancestor_ids):
    """解析 iNaturalist 祖先 ID 为分类名"""
    if not ancestor_ids:
        return {}
    try:
        ids_str = ",".join(str(a) for a in ancestor_ids[:20])
        resp = session.get(f"https://api.inaturalist.org/v1/taxa/{ids_str}",
                          headers={"User-Agent": UA, "Referer": "https://www.inaturalist.org"},
                          timeout=15)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            return {r["id"]: r["name"] for r in results if "name" in r}
    except Exception:
        pass
    return {}


def inat_species(session, scientific_name):
    """从 iNaturalist 获取通用名、图片、分布"""
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

        # 解析祖先获取 family/genus
        ancestors = resolve_ancestors(session, r.get("ancestor_ids", []))
        rank_map = {}
        for aid in r.get("ancestor_ids", []):
            name = ancestors.get(aid, "")
            if name:
                rank_map[str(aid)] = name

        # 找 family 和 genus（通过搜索祖先名中已知的分类名）
        family = None
        genus = None
        for name in ancestors.values():
            if name.lower().endswith("idae") and not family:
                family = name
            if scientific_name.startswith(name) and len(name) > 3:
                genus = name

        # 图片
        photo = r.get("default_photo", {})
        image_data = None
        if photo:
            image_data = {
                "url": photo.get("medium_url") or photo.get("square_url"),
                "attribution": photo.get("attribution", ""),
                "license": photo.get("license_code", ""),
            }

        return {
            "inat_id": r.get("id"),
            "name": r.get("name"),
            "common_name": r.get("preferred_common_name"),
            "english_common_name": r.get("english_common_name"),
            "observations_count": r.get("observations_count", 0),
            "wikipedia_url": r.get("wikipedia_url"),
            "conservation_status": r.get("conservation_status", {}).get("status_name"),
            "photo": image_data,
            "ancestors_by_id": rank_map,
            "family": family,
            "genus": genus,
        }
    except Exception as e:
        print(f"  ⚠️ iNat error: {e}", file=sys.stderr)
    return None


def merge_data(name_cn, sci_name, gbif, inat):
    """合并 GBIF + iNaturalist 数据"""
    result = {
        "name_cn": name_cn,
        "name_latin": gbif.get("scientific_name") if gbif else sci_name,
        "common_name_en": None,
        "family": None,
        "genus": None,
        "class": None,
        "distribution": None,
        "conservation": None,
        "image_url": None,
        "image_attribution": None,
        "wikipedia_url": None,
        "observations_count": 0,
        # 兼容 DB 字段
        "difficulty": None,
        "morph_tier": None,
        "price_range": None,
        "overview": None,
        "traits": {},
        "care_params": {},
        # 元数据
        "sources": {
            "gbif": bool(gbif),
            "inat": bool(inat),
        },
    }

    # GBIF 数据
    if gbif:
        result["name_latin"] = gbif.get("scientific_name")
        result["family"] = gbif.get("family")
        result["genus"] = gbif.get("genus")
        result["class"] = gbif.get("class")

    # iNaturalist 数据
    if inat:
        result["common_name_en"] = inat.get("common_name") or inat.get("english_common_name")
        result["wikipedia_url"] = inat.get("wikipedia_url")
        result["observations_count"] = inat.get("observations_count", 0)
        result["conservation"] = inat.get("conservation_status")

        # iNat family/genus 作为 GBIF 的补充
        if not result["family"] and inat.get("family"):
            result["family"] = inat["family"]
        if not result["genus"] and inat.get("genus"):
            result["genus"] = inat["genus"]

        # 图片
        photo = inat.get("photo")
        if photo:
            result["image_url"] = photo.get("url")
            result["image_attribution"] = photo.get("attribution")
            result["image_license"] = photo.get("license")

    # 置信度
    score = 0
    if result["name_latin"]: score += 20
    if result["family"]: score += 20
    if result["genus"]: score += 15
    if result["common_name_en"]: score += 10
    if result["image_url"]: score += 20
    if result["wikipedia_url"]: score += 10
    if result["observations_count"]: score += 5
    result["_confidence"] = score

    return result


def main():
    session = requests.Session()
    results = []

    print(f"🐢 权威数据源采集：{len(SPECIES)} 个蛋龟品种\n")

    for i, (name_cn, sci_name) in enumerate(SPECIES, 1):
        print(f"[{i}/{len(SPECIES)}] {name_cn} ({sci_name}) ...", end=' ', flush=True)

        # GBIF
        gbif = gbif_taxonomy(sci_name)
        gbif_ok = "✅" if gbif else "❌"

        # iNaturalist
        time.sleep(0.5)  # 短暂间隔
        inat = inat_species(session, sci_name)
        inat_ok = "✅" if inat else "❌"

        # 合并
        species = merge_data(name_cn, sci_name, gbif, inat)
        results.append(species)

        print(f"GBIF:{gbif_ok} iNat:{inat_ok} (置信度 {species['_confidence']}%)")

        if i < len(SPECIES):
            time.sleep(DELAY)

    # 写入 JSON
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 统计
    avg_conf = sum(r["_confidence"] for r in results) / len(results)
    with_img = sum(1 for r in results if r["image_url"])
    with_family = sum(1 for r in results if r["family"])
    with_wiki = sum(1 for r in results if r["wikipedia_url"])

    print(f"\n{'='*55}")
    print(f"📄 {OUTPUT_FILE}")
    print(f"   总数: {len(results)} | 平均置信度: {avg_conf:.0f}%")
    print(f"   有科属: {with_family}/{len(results)} | 有图片: {with_img}/{len(results)} | 有Wiki: {with_wiki}/{len(results)}")
    print(f"   数据源: GBIF + iNaturalist (CC 授权)")

if __name__ == '__main__':
    main()
