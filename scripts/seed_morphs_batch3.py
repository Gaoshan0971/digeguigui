#!/usr/bin/env python3
"""seed_morphs_batch3.py — 奶蛇+肥尾守宫+Tegu+蓝舌 morph种子"""
import sqlite3, json

DB = '/home/ubuntu/digeguigui/data/digeguigui.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# ============================================================
MILKSNAKE_GENES = [
    ("albino","Albino","白化","recessive","color","T-白化，橙白配色"),
    ("anerythristic","Anerythristic","缺红","recessive","reduction","灰黑白配色"),
    ("hypomelanistic","Hypomelanistic","缺黑","recessive","reduction","减淡色系"),
    ("lavender","Lavender","薰衣草","recessive","color","紫调/粉调"),
    ("t_pos_albino","T+ Albino","T+白化","recessive","color","焦糖调"),
    ("stripe","Stripe","直线","recessive","pattern","背中线"),
    ("motley","Motley","圆点","recessive","pattern","圆斑纹"),
    ("tessera","Tessera","镶嵌","dominant","pattern","背纹条状"),
    ("diffused","Diffused","扩散","recessive","pattern","侧纹褪去"),
    ("dilute","Dilute","稀释","recessive","color","全色淡化"),
]
MILKSNAKE_COMBOS = [
    ("Snow","雪白",["albino","anerythristic"],"Albino+Anery","粉白底+淡纹"),
    ("Ghost","幽灵",["hypomelanistic","anerythristic"],"Hypo+Anery","银灰色"),
    ("Lavender Albino","薰衣草白化",["lavender","albino"],"Lavender+Albino","粉紫橙"),
    ("Striped Albino","直线白化",["stripe","albino"],"Stripe+Albino","橙白背线"),
    ("Tessera Albino","镶嵌白化",["tessera","albino"],"Tessera+Albino","条纹橙白"),
]

# ============================================================
TEGU_GENES = [
    ("albino","Albino","白化","recessive","color","T-白化 纯白+粉眼"),
    ("anery","Anerythristic","缺红","recessive","reduction","灰调/银灰"),
    ("hypo","Hypomelanistic","缺黑","recessive","reduction","淡化色"),
    ("purple","Purple/Blizzard","紫/暴风雪","recessive","color","紫色调"),
    ("high_white","High White","高白","polygenic","pattern","高白色侧"),
    ("blue","Blue","蓝","polygenic","color","蓝灰调(选育)"),
    ("red","Red","红","polygenic","color","红调增强(选育)"),
    ("melanistic","Melanistic","黑化","recessive","color","全黑"),
]
TEGU_COMBOS = [
    ("Albino Blue","白化蓝",["albino","blue"],"Albino+Blue","浅蓝白"),
    ("Purple Albino","紫色白化",["purple","albino"],"Purple+Albino","粉紫白化"),
    ("High White Anery","高白缺红",["high_white","anery"],"High White+Anery","银白高白侧"),
    ("Blizzard Tegu","暴风雪",["purple","anery"],"Purple+Anery","银紫无纹"),
]

# ============================================================
BLUETONGUE_GENES = [
    ("albino","Albino","白化","recessive","color","珍贵白化系"),
    ("hypo","Hypomelanistic","缺黑","recessive","reduction","淡化色调"),
    ("hyper_melanistic","Hyper Melanistic","超黑","recessive","color","深黑/纯黑"),
    ("axanthic","Axanthic","缺黄","recessive","reduction","灰/蓝调"),
    ("t_pos_albino","T+ Albino","T+白化","recessive","color","焦糖/橙调"),
    ("sunset","Sunset","日落","polygenic","color","红橙渐变"),
    ("patternless","Patternless","无纹","recessive","pattern","纯色无斑"),
]
BLUETONGUE_COMBOS = [
    ("Sunset Hypo","日落缺黑",["sunset","hypo"],"Sunset+Hypo","浓橙浅色"),
    ("Albino Sunset","白化日落",["albino","sunset"],"Albino+Sunset","橙粉白化"),
    ("Hyper Axanthic","超黑缺黄",["hyper_melanistic","axanthic"],"Hyper Mel+Axanthic","蓝黑调"),
]

# ============================================================
FATTAIL_GENES = [
    ("albino","Albino","白化","recessive","color","T-白化 橙白"),
    ("amel","Amelanistic","缺黑","recessive","color","红/橙底"),
    ("patternless","Patternless","无纹","recessive","pattern","纯色"),
    ("white_out","White Out","白化输出","recessive","color","高白色"),
    ("caramel","Caramel","焦糖","recessive","color","焦糖色"),
    ("oreo","Oreo","奥利奥","recessive","color","黑白配"),
    ("ghost","Ghost","幽灵","recessive","reduction","银灰调"),
    ("stripe","Stripe","直线","recessive","pattern","背中线"),
    ("zulu","Zulu","祖鲁","recessive","pattern","点斑背纹"),
    ("zero","Zero","零","recessive","color","纯黑/深灰"),
]
FATTAIL_COMBOS = [
    ("White Out Albino","白化输出白化",["white_out","albino"],"White Out+Albino","纯白+粉纹"),
    ("Caramel Albino","焦糖白化",["caramel","albino"],"Caramel+Albino","焦糖橙"),
    ("Ghost Albino","幽灵白化",["ghost","albino"],"Ghost+Albino","淡银橙"),
    ("Oreo Ghost","奥利奥幽灵",["oreo","ghost"],"Oreo+Ghost","银白黑"),
    ("Zero Patternless","零无纹",["zero","patternless"],"Zero+Patternless","纯黑无纹"),
]

SPECIES_MAP = {
    'milk':  ('Lampropeltis triangulum', MILKSNAKE_GENES, MILKSNAKE_COMBOS),
    'tegu':  ('Salvator merianae', TEGU_GENES, TEGU_COMBOS),
    'blue':  ('Tiliqua scincoides', BLUETONGUE_GENES, BLUETONGUE_COMBOS),
    'fat':   ('Hemitheconyx caudicinctus', FATTAIL_GENES, FATTAIL_COMBOS),
}

insGene = "INSERT OR IGNORE INTO morph_genes (gene_symbol,gene_name,gene_name_cn,inheritance,category,is_proven,description) VALUES (?,?,?,?,?,1,?)"
insMorph = "INSERT OR IGNORE INTO species_morphs (species_id,gene_id,morph_name,morph_name_cn,is_base_morph) VALUES (?,?,?,?,1)"

total_genes = 0
total_combos = 0

for key, (latin, genes, combos) in SPECIES_MAP.items():
    sp = cur.execute("SELECT species_id, name_cn FROM species WHERE name_latin LIKE ?", (latin+'%',)).fetchone()
    if not sp:
        print(f"⚠️  未找到: {latin}")
        continue
    
    print(f"🧬 {sp[1]} (id={sp[0]}) — {len(genes)}基因 + {len(combos)}组合")
    
    for sym, name, cn, inherit, cat, desc in genes:
        cur.execute(insGene, (sym, name, cn, inherit, cat, desc))
        gid = cur.execute("SELECT gene_id FROM morph_genes WHERE gene_symbol=?", (sym,)).fetchone()[0]
        cur.execute(insMorph, (sp[0], gid, name, cn))
        total_genes += 1
    
    for cname, cname_cn, gene_syms, formula, desc in combos:
        gene_ids = []
        for gs in gene_syms:
            r = cur.execute("SELECT gene_id FROM morph_genes WHERE gene_symbol=?", (gs,)).fetchone()
            if r: gene_ids.append(r[0])
        if gene_ids:
            cur.execute("""
                INSERT OR IGNORE INTO morph_combinations (species_id, combo_name, combo_name_cn, gene_ids, combo_formula, description)
                VALUES (?,?,?,?,?,?)
            """, (sp[0], cname, cname_cn, json.dumps(gene_ids), formula, desc))
            total_combos += 1

conn.commit()
print(f"\n✅ 本批: {total_genes}基因 + {total_combos}组合")
print(f"📊 累计: {cur.execute('SELECT COUNT(*) FROM morph_genes').fetchone()[0]}基因 | {cur.execute('SELECT COUNT(*) FROM morph_combinations').fetchone()[0]}组合")

conn.close()
