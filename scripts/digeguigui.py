#!/usr/bin/env python3
"""
digeguigui — 爬宠异宠基因库 CLI 工具
用法: python3 digeguigui.py <command> [args...]
"""
import sqlite3
import json
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, '..', 'data', 'digeguigui.db')

if not os.path.exists(DB):
    print(f"❌ 数据库不存在: {DB}")
    sys.exit(1)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()


def cmd_species(args):
    """搜索物种: digeguigui species [category=龟|蛇|蜥蜴|蛙|守宫] [query]"""
    cat = None
    query = None
    for a in args:
        if a in ('龟','蛇','蜥蜴','蛙','守宫'):
            cat = a
        else:
            query = a
    
    sql = "SELECT species_id, name_cn, name_latin, family, category, observations_count, image_url FROM species WHERE 1=1"
    params = []
    if cat:
        sql += " AND category = ?"
        params.append(cat)
    if query:
        sql += " AND (name_cn LIKE ? OR name_latin LIKE ? OR common_name_en LIKE ?)"
        params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
    
    sql += " ORDER BY category, name_cn LIMIT 50"
    rows = cur.execute(sql, params).fetchall()
    
    if not rows:
        print("未找到匹配物种")
        return
    
    print(f"\n{'ID':>4}  {'中文名':16s} {'拉丁名':45s} {'科':20s} {'品类':6s} {'观察':>6s}")
    print("-" * 105)
    for r in rows:
        lat = r['name_latin'][:43] + '..' if len(r['name_latin'])>45 else r['name_latin']
        print(f"{r['species_id']:4d}  {r['name_cn']:16s} {lat:45s} {(r['family'] or '')[:18]:20s} {r['category']:6s} {r['observations_count'] or 0:>6d}")
    print(f"\n共 {len(rows)} 条 (限制50)")


def cmd_info(args):
    """查看详情: digeguigui info <species_id|name>"""
    if not args:
        print("用法: digeguigui info <id|中文名|拉丁名>")
        return
    
    q = args[0]
    # Try ID first
    r = cur.execute("SELECT * FROM species WHERE species_id=? OR name_cn=? OR name_latin LIKE ?",
                    (q, q, f'%{q}%')).fetchone()
    if not r:
        # Try wider search
        r = cur.execute("SELECT * FROM species WHERE name_cn LIKE ? OR name_latin LIKE ? LIMIT 1",
                        (f'%{q}%', f'%{q}%')).fetchone()
    if not r:
        print(f"未找到: {q}")
        return
    
    print(f"\n🐾 {r['name_cn']} ({r['name_latin']})")
    print(f"   科: {r['family']} | 属: {r['genus']} | 品类: {r['category']}")
    if r['distribution']:
        print(f"   分布: {r['distribution'][:120]}")
    if r['habitat']:
        print(f"   栖息地: {r['habitat'][:120]}")
    if r['conservation']:
        print(f"   保护: {r['conservation']}")
    if r['reproduction']:
        print(f"   繁殖: {r['reproduction'][:60]}")
    if r['wikipedia_url']:
        print(f"   Wiki: {r['wikipedia_url']}")
    print(f"   图片: {r['image_url'] or '无'}")
    print(f"   来源: {r['image_attribution'] or '无'}")


def cmd_morph(args):
    """查看品系: digeguigui morph <species_query>"""
    if not args:
        print("用法: digeguigui morph <玉米蛇|球蟒|豹纹守宫|species_id>")
        return
    
    q = ' '.join(args)
    sp = cur.execute("SELECT species_id, name_cn FROM species WHERE name_cn LIKE ? OR name_latin LIKE ? LIMIT 1",
                     (f'%{q}%', f'%{q}%')).fetchone()
    if not sp:
        print(f"未找到品种: {q}")
        return
    
    # Genes
    genes = cur.execute("""
        SELECT g.gene_symbol, g.gene_name, g.gene_name_cn, g.inheritance, g.category, g.description
        FROM species_morphs sm
        JOIN morph_genes g ON sm.gene_id = g.gene_id
        WHERE sm.species_id = ?
        ORDER BY g.inheritance, g.gene_name
    """, (sp['species_id'],)).fetchall()
    
    if genes:
        print(f"\n🧬 {sp['name_cn']} — {len(genes)} 个基因")
        emoji = {'recessive':'🟡','dominant':'🟢','codominant':'🔵','polygenic':'🟣'}
        print(f"{'符号':20s} {'名称':25s} {'中文':12s} {'遗传':12s} {'类别'}")
        print("-" * 80)
        for g in genes:
            e = emoji.get(g['inheritance'], '⚪')
            print(f"{e} {g['gene_symbol']:17s} {g['gene_name']:25s} {g['gene_name_cn']:12s} {g['inheritance']:12s} {g['category']}")
    
    # Combos
    combos = cur.execute("""
        SELECT combo_name, combo_name_cn, combo_formula, description
        FROM morph_combinations
        WHERE species_id = ?
        ORDER BY combo_name
    """, (sp['species_id'],)).fetchall()
    
    if combos:
        print(f"\n🎨 {len(combos)} 个组合品系")
        for c in combos:
            print(f"  {c['combo_name']:30s} [{c['combo_name_cn']:10s}] {c['combo_formula']}")


def cmd_calc(args):
    """基因计算: digeguigui calc 'het amel anery' 'het amel anery' [species]"""
    if len(args) < 2:
        print("用法: digeguigui calc '亲本1基因型' '亲本2基因型' [品种]")
        print('示例: digeguigui calc "het amel anery" "het amel anery"')
        return
    
    parent1 = args[0]
    parent2 = args[1]
    species = args[2] if len(args) > 2 else None
    
    sys.path.insert(0, HERE)
    from genecalc import parse_genotype, punnett, format_table
    p1 = parse_genotype(parent1)
    p2 = parse_genotype(parent2)
    results = punnett(p1, p2, species)
    print(format_table(results))


def cmd_stats(args=None):
    """统计: digeguigui stats"""
    cats = cur.execute("SELECT category, COUNT(*) as cnt FROM species GROUP BY category ORDER BY cnt DESC").fetchall()
    print("\n📊 滴个龟龟基因库")
    print(f"{'品类':10s} {'物种数':>6s}")
    print("-" * 20)
    for c in cats:
        print(f"{c['category']:10s} {c['cnt']:6d}")
    total = cur.execute("SELECT COUNT(*) FROM species").fetchone()[0]
    print(f"{'━━━━━━━━━━':10s} {'━━━━':>6s}")
    print(f"{'总计':10s} {total:6d}")
    
    # Family count
    fams = cur.execute("SELECT COUNT(DISTINCT family) FROM species WHERE family != ''").fetchone()[0]
    genes = cur.execute("SELECT COUNT(*) FROM morph_genes").fetchone()[0]
    combos = cur.execute("SELECT COUNT(*) FROM morph_combinations").fetchone()[0]
    print(f"\n  {fams} 科 | {genes} 基因 | {combos} 组合品系")


def cmd_help(args=None):
    """帮助"""
    print("""
🐢 滴个龟龟 CLI — 爬宠异宠基因库

用法: python3 digeguigui.py <命令> [参数]

命令:
  species [品类] [搜索词]    搜索物种
  info <id|中文名|拉丁名>    查看物种详情
  morph <品种名>              查看品系基因+组合
  calc '亲本1' '亲本2' [品种]  Punnett基因计算器
  stats                       数据库统计
  help                        帮助

示例:
  digeguigui.py species 蛇 王蛇
  digeguigui.py info 448
  digeguigui.py morph 球蟒
  digeguigui.py calc 'het amel anery' 'het amel anery'
  digeguigui.py stats
""")


COMMANDS = {
    'species': cmd_species,  's': cmd_species,
    'info': cmd_info,        'i': cmd_info,
    'morph': cmd_morph,      'm': cmd_morph,
    'calc': cmd_calc,        'c': cmd_calc,
    'stats': cmd_stats,      'st': cmd_stats,
    'help': cmd_help,        'h': cmd_help,
}

if __name__ == '__main__':
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    rest = sys.argv[2:]
    
    if cmd in COMMANDS:
        COMMANDS[cmd](rest)
    else:
        print(f"未知命令: {cmd}")
        cmd_help()
    
    conn.close()
