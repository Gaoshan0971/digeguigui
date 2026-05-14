#!/usr/bin/env python3
"""
scrape_morphs_cornsnake.py — 从 Ian's Vivarium 爬取玉米蛇基因数据
用法: /usr/bin/python3 scripts/scrape_morphs_cornsnake.py
输出: data/morphs_cornsnake.json
"""
import requests
import json
import time
import sys
import os
import re

BASE_URL = "https://iansvivarium.com/morphs/"
UA = "Mozilla/5.0 (compatible; Digeguigui/1.0; research project)"
DELAY = 1.5
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "morphs_cornsnake.json")

# Known inheritance types for corn snake genes (verified from morph guides)
KNOWN_INHERITANCE = {
    # Recessive
    "amelanistic": ("recessive", "Amelanistic", "白化"),
    "anerythristic": ("recessive", "Anerythristic A", "缺红A型"),
    "charcoal": ("recessive", "Anerythristic B (Charcoal)", "缺红B型/炭黑"),
    "caramel": ("recessive", "Caramel", "焦糖"),
    "lavender": ("recessive", "Lavender", "薰衣草"),
    "diffused": ("recessive", "Diffused / Bloodred", "扩散/血红"),
    "hypomelanistic": ("recessive", "Hypomelanistic A", "减黑A型"),
    "cinder": ("recessive", "Cinder / Ashy", "灰烬"),
    "kastanie": ("recessive", "Kastanie", "栗色"),
    "dilute": ("recessive", "Dilute", "稀释"),
    "lava": ("recessive", "Lava", "熔岩"),
    "motley": ("recessive", "Motley", "花色"),
    "stripe": ("recessive", "Stripe", "条纹"),
    "scaleless": ("recessive", "Scaleless", "无鳞"),
    "palmetto": ("recessive", "Palmetto", "棕榈"),
    "terrazzo": ("recessive", "Terrazzo", "水磨石"),
    "toffee": ("recessive", "Toffee", "太妃糖"),
    "buf": ("recessive", "Buf", "水牛"),
    "microscale": ("recessive", "Microscale", "微鳞"),
    "pied_sided": ("recessive", "Pied Sided", "侧边花斑"),
    "strawberry": ("recessive", "Strawberry", "草莓"),
    "sunrise": ("recessive", "Sunrise", "日出"),
    "red_coat": ("recessive", "Red Coat", "红衣"),
    "green_blotch": ("recessive", "Green Blotch", "绿斑"),
    "christmas": ("recessive", "Christmas", "圣诞"),
    "halo": ("recessive", "Halo", "光环"),
    "masque": ("recessive", "Masque", "面具"),
    # Dominant / Incomplete Dominant
    "tessera": ("dominant", "Tessera", "镶嵌"),
    "ultra": ("codominant", "Ultra", "超白化"),
    "sunkissed": ("recessive", "Sunkissed", "阳光之吻"),
    "black_diamond": ("recessive", "Black Diamond", "黑钻"),
}


def scrape_gene_detail(session, gene_slug):
    """Scrape individual gene detail page"""
    url = f"{BASE_URL}?m={gene_slug}"
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return {}
        html = resp.text

        data = {}

        # Genetics info
        genetics_block = re.search(r'<b>Genetics:</b>(.*?)(?:</div>|</ul>)', html, re.DOTALL)
        if genetics_block:
            block = genetics_block.group(1)
            # Check inheritance type
            if 'Recessive' in block:
                data['inheritance'] = 'recessive'
            elif 'Incomplete Dominant' in block or 'Co-dominant' in block:
                data['inheritance'] = 'codominant'
            elif 'Dominant' in block:
                data['inheritance'] = 'dominant'
            else:
                data['inheritance'] = 'unknown'

        # Allelic info
        allelic = re.findall(r'Allelic with:.*?<a[^>]*>([^<]+)</a>', html, re.DOTALL)
        if allelic:
            data['allelic_with'] = [a.strip() for a in allelic]

        # Related genes from genetics block
        genes = re.findall(r'<a href=\"/morphs\?m=([^\"]+)\">([^<]+)</a>', html)
        if genes:
            data['related_genes'] = [g[0] for g in genes if g[0] != gene_slug]

        # Check for "het" mentions
        het_mentions = re.findall(r'het\s+([A-Z][a-zA-Z]+)', html)
        if het_mentions:
            data['het_mentions'] = list(set(het_mentions))

        return data
    except Exception as e:
        print(f"  ⚠️  Error scraping {gene_slug}: {e}", file=sys.stderr)
        return {}


def scrape_all_genes(session):
    """Scrape the main morph listing page and extract all genes"""
    print("📡 Fetching morph listing page...")
    resp = session.get(BASE_URL, timeout=20)
    if resp.status_code != 200:
        print(f"❌ Failed to fetch morph page: {resp.status_code}")
        return []

    html = resp.text

    # Extract all morph entries with their gene combinations
    entries = re.findall(
        r'<a href=\"\.\/\?m=([^&\"]+)[^\"]*\">([^<]+)</a>'
        r'(?:\s*<i[^>]*>([^<]*)</i>)?'
        r'<span class=\"ivcombo\">([^<]*)</span>',
        html
    )

    # Extract section info: map morphs to their sections
    sections = {}
    current_section = None
    for line in html.split('\n'):
        sec_match = re.search(r'<li id=\"([^\"]+)\" class=\"morphlist-header\"><h2>([^<]+)</h2>', line)
        if sec_match:
            current_section = sec_match.group(2)

        morph_match = re.search(r'<a href=\"\.\/\?m=([^&\"]+)[^\"]*\">', line)
        if morph_match and current_section:
            sections[morph_match.group(1)] = current_section

    # Build comprehensive gene list
    all_genes = {}
    gene_info = {}

    for m_id, morph_name, aka, combo in entries:
        combo = combo.strip()
        if not combo or combo == 'Wildtype':
            continue

        # Parse individual genes from combo string
        genes_in_combo = [g.strip() for g in combo.split(' + ')]
        for gene in genes_in_combo:
            if gene.startswith('het ') or gene == 'Unknown' or gene == 'Gene X':
                continue
            gene_normalized = gene.lower().replace(' ', '_')
            if gene_normalized not in gene_info:
                gene_info[gene_normalized] = {
                    'gene_symbol': gene_normalized,
                    'gene_name': gene,
                    'gene_name_cn': '',
                    'inheritance': 'unknown',
                    'category': '',
                    'source_url': f"{BASE_URL}?m={gene_normalized}",
                    'appears_in_combos': [],
                }
            gene_info[gene_normalized]['appears_in_combos'].append((m_id, morph_name, combo))

    print(f"📊 Found {len(gene_info)} unique genes in {len(entries)} morph entries")

    # Enrich with known data
    for gene_slug, info in gene_info.items():
        if gene_slug in KNOWN_INHERITANCE:
            inh, full_name, cn_name = KNOWN_INHERITANCE[gene_slug]
            info['inheritance'] = inh
            if full_name:
                info['gene_name'] = full_name
            if cn_name:
                info['gene_name_cn'] = cn_name

        # Determine category
        gene_lower = gene_slug.lower()
        if any(t in gene_lower for t in ['amel', 'albino', 'ultra', 'lavender', 'caramel', 'lava', 'toffee', 'buf', 'sunkissed']):
            info['category'] = 'color'
        elif any(t in gene_lower for t in ['anery', 'charcoal', 'hypo', 'cinder', 'ghost', 'dilute']):
            info['category'] = 'reduction'
        elif any(t in gene_lower for t in ['motley', 'stripe', 'tessera', 'diffused', 'bloodred', 'pied', 'terrazzo', 'palmetto', 'aztec', 'zigzag']):
            info['category'] = 'pattern'
        elif any(t in gene_lower for t in ['scaleless', 'microscale']):
            info['category'] = 'scale'
        else:
            info['category'] = 'other'

        # Section info
        if gene_slug in sections:
            info['section'] = sections[gene_slug]

    return gene_info


def main():
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    print("🐍 玉米蛇基因数据采集 — Ian's Vivarium")
    print("=" * 50)

    # Step 1: Get all genes from listing
    gene_info = scrape_all_genes(session)

    # Step 2: Scrape detail pages for additional info
    print(f"\n🔍 Scraping detail pages for {len(gene_info)} genes...")
    detail_count = 0
    for i, (gene_slug, info) in enumerate(gene_info.items(), 1):
        print(f"  [{i}/{len(gene_info)}] {gene_slug}...", end=" ", flush=True)
        detail = scrape_gene_detail(session, gene_slug)
        if detail:
            for k, v in detail.items():
                if v and k not in info:
                    info[k] = v
            detail_count += 1
            print("✅")
        else:
            print("❌ (no detail)")

        if i < len(gene_info):
            time.sleep(DELAY)

    # Step 3: Build seed data
    genes_output = []
    for gene_slug, info in sorted(gene_info.items()):
        genes_output.append({
            "gene_symbol": info['gene_symbol'],
            "gene_name": info['gene_name'],
            "gene_name_cn": info.get('gene_name_cn', ''),
            "inheritance": info.get('inheritance', 'unknown'),
            "category": info.get('category', 'other'),
            "description": "",
            "year_discovered": info.get('year_discovered'),
            "discoverer": info.get('discoverer', ''),
            "first_produced_by": info.get('first_produced_by', ''),
            "is_proven": 1,
            "source_url": info.get('source_url', ''),
            "allelic_with": info.get('allelic_with', []),
            "combo_count": len(info.get('appears_in_combos', [])),
        })

    # Write output
    output = {
        "species": "Pantherophis guttatus",
        "species_id": 448,
        "common_name": "玉米蛇 / Corn Snake",
        "gene_count": len(genes_output),
        "genes": genes_output,
        "source": "https://iansvivarium.com/morphs/",
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"📄 Output: {OUTPUT}")
    print(f"   Total genes: {len(genes_output)}")
    print(f"   Detail pages scraped: {detail_count}/{len(gene_info)}")

    # Summary by inheritance
    by_inh = {}
    for g in genes_output:
        inh = g['inheritance']
        by_inh[inh] = by_inh.get(inh, 0) + 1
    print(f"   By inheritance: {by_inh}")

    by_cat = {}
    for g in genes_output:
        cat = g['category']
        by_cat[cat] = by_cat.get(cat, 0) + 1
    print(f"   By category: {by_cat}")


if __name__ == '__main__':
    main()
