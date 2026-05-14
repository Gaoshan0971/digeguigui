#!/usr/bin/env python3
"""
genecalc.py — 啮宠基因计算器
从 morph JSON 数据加载基因库，Punnett 方阵计算子代概率
"""
import json, os
from itertools import product

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')

# ---- Load gene DB from JSON files ----
def load_gene_db():
    db = {}
    sources = {
        'morphs_cornsnake.json': 'corn',
        'morphs_ballpython.json': 'ball',
        'morphs_leopardgecko.json': 'gecko',
    }
    for fname, sp in sources.items():
        fp = os.path.join(DATA, fname)
        if not os.path.exists(fp):
            continue
        with open(fp) as f:
            d = json.load(f)
        for g in d['genes']:
            sym = g['gene_symbol'].lower()
            db[sym] = {
                'name': g['gene_name'],
                'cn': g['gene_name_cn'] or g['gene_name'],
                'inherit': g.get('inheritance', 'recessive'),
                'species': sp,
                'category': g.get('category', ''),
            }
    # Short aliases
    aliases = {
        'amel': 'amelanistic', 'anery': 'anerythristic', 'hypo': 'hypomelanistic',
        'bloodred': 'diffused', 'stripe': 'stripe', 'motley': 'motley',
        'lav': 'lavender', 'char': 'charcoal',
    }
    for alias, target in aliases.items():
        if target in db:
            db[alias] = dict(db[target])
            db[alias]['alias_for'] = target
    
    return db

GENE_DB = load_gene_db()


def parse_genotype(s):
    """Parse genotype string like 'het amel anery visual motley stripe'
    States: 'het' = heterozygous, 'visual' = homozygous (visual morph), default = het if just gene name
    """
    genes = {}
    s = s.strip().lower()
    if not s:
        return genes
    
    parts = s.replace(',', ' ').split()
    i = 0
    current_state = 'het'  # default: bare gene names = het
    
    while i < len(parts):
        p = parts[i]
        if p in ('het', '66%het', '50%het', 'ph'):
            current_state = 'het'
            i += 1
            continue
        if p in ('visual', 'vis', 'super', 'homo'):
            current_state = 'visual'
            i += 1
            continue
        
        # Check if it's a gene symbol
        if p in GENE_DB:
            genes[p] = current_state
        elif p.endswith('/') and p[:-1] in GENE_DB:
            genes[p[:-1]] = current_state
        
        i += 1
    
    return genes


def punnett(parent1, parent2, species_filter=None):
    """Punnett square for multi-gene crosses"""
    all_genes = set(parent1.keys()) | set(parent2.keys())
    if species_filter:
        all_genes = {g for g in all_genes if GENE_DB.get(g, {}).get('species') == species_filter}
    
    results = []
    for gene in sorted(all_genes):
        info = GENE_DB.get(gene)
        if not info:
            continue
        
        p1 = parent1.get(gene, 'wt')
        p2 = parent2.get(gene, 'wt')
        inh = info['inherit']
        
        def gametes(state):
            if inh == 'dominant':
                # One copy is dominant. visual = same as het
                if state in ('het', 'visual'):
                    return [(gene, 1)]  # 1 copy → visual
                else:
                    return [('+', 1)]
            elif inh == 'codominant':
                if state == 'visual':
                    return [(gene.upper(), 1)]  # homozygous
                elif state == 'het':
                    return [(gene, 0.5), ('+', 0.5)]
                else:
                    return [('+', 1)]
            else:  # recessive
                if state == 'visual':
                    return [(gene, 1)]
                elif state == 'het':
                    return [(gene, 0.5), ('+', 0.5)]
                else:
                    return [('+', 1)]
        
        g1 = gametes(p1)
        g2 = gametes(p2)
        
        # Punnett square
        combos = []
        for a, pa in g1:
            for b, pb in g2:
                combos.append((sorted([a, b]), pa * pb))
        
        # Merge identical combos
        from collections import Counter
        combo_counts = Counter()
        for genes_pair, prob in combos:
            key = '+'.join(sorted(genes_pair))
            combo_counts[key] += prob
        
        # Round and normalize
        total = sum(combo_counts.values())
        probs = {}
        for combo, cnt in combo_counts.items():
            pct = cnt / total if total > 0 else 0
            genes_list = [x for x in combo.split('+') if x != '+']
            
            if inh == 'dominant':
                if any(x != '+' for x in genes_list if x != '+'):
                    probs[f"Visual {info['cn']}"] = pct
                else:
                    probs["Normal"] = pct
            elif inh == 'codominant':
                lowers = [x for x in genes_list if x.islower()]
                uppers = [x for x in genes_list if x.isupper()]
                total_copies = len(lowers) + len(uppers)
                if total_copies >= 2:
                    probs[f"Super {info['cn']}"] = pct
                elif total_copies == 1:
                    probs[f"{info['cn']}"] = pct
                else:
                    probs["Normal"] = pct
            else:  # recessive
                if len([x for x in genes_list if x.islower()]) == 2:
                    probs[f"Visual {info['cn']}"] = pct
                elif len([x for x in genes_list if x.islower()]) == 1:
                    probs[f"het {info['cn']}"] = pct
                else:
                    probs["Normal"] = pct
        
        results.append({
            'gene': gene, 'name': info['name'], 'cn': info['cn'],
            'inherit': inh, 'probabilities': probs
        })
    
    return results


def format_table(results):
    """Pretty-print Punnett results"""
    lines = [
        "\n╔══════════════════════════════════════════════════╗",
        "║         🧬 啮宠基因计算器 (Punnett)             ║",
        "╚══════════════════════════════════════════════════╝",
    ]
    
    for r in results:
        emoji = {'recessive': '🟡', 'dominant': '🟢', 'codominant': '🔵', 'polygenic': '🟣'}.get(r['inherit'], '⚪')
        lines.append(f"\n  {emoji} {r['gene']:18s} [{r['name']:22s} | {r['cn']:8s} | {r['inherit']:12s}]")
        
        for pheno, prob in sorted(r['probabilities'].items(), key=lambda x: -x[1]):
            bar_len = max(1, int(prob * 20))
            bar = '█' * bar_len + '░' * (20 - bar_len)
            pct = f"{prob*100:.0f}%"
            lines.append(f"    │{bar}│ {pct:>4s}  {pheno}")
    
    # Multi-gene summary
    lines.append(f"\n  📋 单一基因位点共 {len(results)} 个（组合表型 = 各基因位点概率相乘）")
    
    return '\n'.join(lines)


# CLI
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("🧬 啮宠基因计算器 — 用法:")
        print()
        print("  python3 genecalc.py 'P1基因型' 'P2基因型' [物种过滤]")
        print()
        print("  语法:")
        print("    homozygote = visual Amel / vis Anery")
        print("    het         = het Amel 或直接写 gene名（默认het）")
        print("    multi-gene  = het Amel Anery visual Motley")
        print()
        print("  示例:")
        print("    # 玉米蛇 Amel x Anery (双het配对)")
        print("    python3 genecalc.py 'het amel' 'het anery'")
        print()
        print("    # 球蟒 Pastel Mojave x Pastel")
        print("    python3 genecalc.py 'pastel mojave' 'pastel' ball")
        print()
        print(f"  已加载 {len(GENE_DB)} 个基因定义")
        sys.exit(1)
    
    p1 = parse_genotype(sys.argv[1])
    p2 = parse_genotype(sys.argv[2])
    species = sys.argv[3] if len(sys.argv) > 3 else None
    
    print(f"\n  👨 亲本1: {p1 if p1 else 'Wild Type (Normal)'}")
    print(f"  👩 亲本2: {p2 if p2 else 'Wild Type (Normal)'}")
    
    results = punnett(p1, p2, species)
    if not results:
        print("\n  ⚠️ 未识别到有效基因，请检查基因名拼写。")
        print(f"  可用基因: {', '.join(sorted(GENE_DB.keys())[:30])}...")
        sys.exit(1)
    
    print(format_table(results))
