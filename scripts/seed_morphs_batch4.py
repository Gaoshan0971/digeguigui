#!/usr/bin/env python3
"""seed_morphs_batch4.py — 红尾蚺/地毯蟒/奶蛇补全 + 全物种组合扩展"""
import sqlite3, json

DB = '/home/ubuntu/digeguigui/data/digeguigui.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# ============================================================
# 红尾蚺 (Boa imperator)
# ============================================================
BOA_GENES = [
    ("albino", "Kahl Albino", "Kahl白化", "recessive", "color", "经典T-白化"),
    ("sharp_albino", "Sharp Albino", "Sharp白化", "recessive", "color", "不同血系白化"),
    ("hypo", "Hypomelanistic", "缺黑", "codominant", "reduction", "淡化色"),
    ("jungle", "Jungle", "丛林", "codominant", "pattern", "乱纹/条纹"),
    ("motley", "Motley", "莫特利", "codominant", "pattern", "圆斑+背线"),
    ("arabesque", "Arabesque", "藤蔓纹", "codominant", "pattern", "阿拉伯藤蔓纹"),
    ("anery", "Anerythristic", "缺红", "recessive", "reduction", "灰黑白"),
    ("aztec", "Aztec", "阿兹特克", "codominant", "pattern", "几何碎纹"),
    ("blood", "Blood", "血红", "recessive", "color", "深红色调"),
    ("leopard", "Leopard", "豹纹", "recessive", "pattern", "碎斑"),
    ("img", "IMG", "黑色素增强", "codominant", "reduction", "增黑色调渐变"),
    ("t_pos", "T+ Albino", "T+白化", "recessive", "color", "焦糖/橙白化"),
    ("ghost", "Ghost", "幽灵", "recessive", "reduction", "Hypo+Anery"),
    ("snow", "Snow", "雪", "recessive", "color", "Albino+Anery 粉白"),
    ("scoria", "Scoria", "熔岩", "codominant", "color", "红棕深色"),
    ("vpi_t_pos", "VPI T+", "VPI T+白化", "recessive", "color", "橙焦糖"),
]
BOA_COMBOS = [
    ("Moonglow", "月光", ["hypo","anery","albino"], "Hypo+Anery+Albino", "淡蓝灰白"),
    ("Sunglow", "日光", ["hypo","albino"], "Hypo+Albino", "鲜橙白化"),
    ("Ghost", "幽灵", ["hypo","anery"], "Hypo+Anery", "银灰色"),
    ("Snow", "雪", ["albino","anery"], "Albino+Anery", "粉白"),
    ("Jungle Hypo", "丛林缺黑", ["jungle","hypo"], "Jungle+Hypo", "乱纹淡化"),
    ("Motley Jungle", "莫特利丛林", ["motley","jungle"], "Motley+Jungle", "融合纹"),
    ("Blood Jungle", "血红丛林", ["blood","jungle"], "Blood+Jungle", "深红乱纹"),
    ("Hypo Motley", "缺黑莫特利", ["hypo","motley"], "Hypo+Motley", "淡化圆斑"),
    ("Ghost Jungle", "幽灵丛林", ["ghost","jungle"], "Ghost+Jungle", "银灰乱纹"),
]

# ============================================================
# 地毯蟒 (Morelia spilota)
# ============================================================
CARPET_GENES = [
    ("albino", "Albino", "白化", "recessive", "color", "T-白化 橙白"),
    ("caramel", "Caramel", "焦糖", "recessive", "color", "焦糖/金黄"),
    ("hypo", "Hypomelanistic", "缺黑", "recessive", "reduction", "淡化"),
    ("axanthic", "Axanthic", "缺黄", "recessive", "reduction", "灰蓝调"),
    ("jaguar", "Jaguar", "美洲豹", "codominant", "pattern", "碎纹+减侧纹"),
    ("zebra", "Zebra", "斑马", "recessive", "pattern", "细横条纹"),
    ("tiger", "Tiger", "老虎", "recessive", "pattern", "粗横条"),
    ("granite", "Granite", "花岗岩", "incomplete_dominant", "pattern", "细密斑"),
    ("stripe", "Stripe", "直线", "recessive", "pattern", "背中线"),
    ("ghost", "Ghost", "幽灵", "recessive", "reduction", "银灰淡化"),
]
CARPET_COMBOS = [
    ("Jaguar Carpet", "豹纹地毯", ["jaguar"], "Jaguar het", "碎纹型"),
    ("Zebra Jaguar", "斑马豹", ["zebra","jaguar"], "Zebra+Jaguar", "条纹碎斑"),
    ("Albino Jaguar", "白化豹", ["albino","jaguar"], "Albino+Jaguar", "橙白碎纹"),
    ("Ghost Jag", "幽灵豹", ["ghost","jaguar"], "Ghost+Jaguar", "银灰碎纹"),
    ("Caramel Coastal", "焦糖海岸", ["caramel"], "Caramel morph", "金黄底"),
    ("Axanthic Jag", "缺黄豹", ["axanthic","jaguar"], "Axanthic+Jaguar", "灰蓝碎纹"),
]

# ============================================================
# 奶蛇补完 — 更多组合
# ============================================================
MILK_EXTRA_COMBOS = [
    ("Tessera Motley", "镶嵌圆点", ["tessera","motley"], "Tessera+Motley", "条纹圆斑"),
    ("Lavender Motley", "薰衣草圆点", ["lavender","motley"], "Lavender+Motley", "紫圆斑"),
    ("Striped Ghost", "直线幽灵", ["stripe","anerythristic","hypomelanistic"], "Stripe+Ghost", "银灰直线"),
    ("Dilute Anery", "稀释缺红", ["dilute","anerythristic"], "Dilute+Anery", "淡灰"),
    ("T+ Albino Motley", "T+白化圆点", ["t_pos_albino","motley"], "T+Albino+Motley", "焦糖圆斑"),
]

# ============================================================
# 肥尾守宫补完 — 更多组合
# ============================================================
FATTAIL_EXTRA_COMBOS = [
    ("White Out Oreo", "白化奥利奥", ["white_out","oreo"], "White Out+Oreo", "高白黑白配"),
    ("Zulu Ghost", "祖鲁幽灵", ["zulu","ghost"], "Zulu+Ghost", "点斑银灰"),
    ("Caramel Patternless", "焦糖无纹", ["caramel","patternless"], "Caramel+Patternless", "焦糖纯色"),
    ("Stripe Zulu", "直线祖鲁", ["stripe","zulu"], "Stripe+Zulu", "背线+点斑"),
    ("Oreo Zero", "奥利奥零", ["oreo","zero"], "Oreo+Zero", "黑白纯黑"),
]

SPECIES_MAP = {
    'boa':    ('Boa imperator', BOA_GENES, BOA_COMBOS),
    'carpet': ('Morelia spilota', CARPET_GENES, CARPET_COMBOS),
}

EXTRA_COMBOS = [
    (451, MILK_EXTRA_COMBOS),   # 奶蛇
    (460, FATTAIL_EXTRA_COMBOS), # 肥尾守宫
]

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

# Extra combos for existing species
for sp_id, combos in EXTRA_COMBOS:
    sp = cur.execute("SELECT name_cn FROM species WHERE species_id=?", (sp_id,)).fetchone()
    if not sp: continue
    for cname, cname_cn, gene_syms, formula, desc in combos:
        gene_ids = []
        for gs in gene_syms:
            r = cur.execute("SELECT gene_id FROM morph_genes WHERE gene_symbol=?", (gs,)).fetchone()
            if r: gene_ids.append(r[0])
        if gene_ids:
            cur.execute("""INSERT OR IGNORE INTO morph_combinations (species_id, combo_name, combo_name_cn, gene_ids, combo_formula, description)
                VALUES (?,?,?,?,?,?)""", (sp_id, cname, cname_cn, json.dumps(gene_ids), formula, desc))
            total_combos += 1

conn.commit()
print(f"\n✅ 本批: {total_genes}基因 + {total_combos}组合")
print(f"📊 累计: {cur.execute('SELECT COUNT(*) FROM morph_genes').fetchone()[0]}基因 | {cur.execute('SELECT COUNT(*) FROM morph_combinations').fetchone()[0]}组合")

# Per species summary
for row in cur.execute("""
    SELECT s.name_cn, COUNT(DISTINCT g.gene_id) as gene_cnt, 
           COUNT(DISTINCT c.combo_id) as combo_cnt
    FROM species s
    LEFT JOIN species_morphs sm ON s.species_id=sm.species_id
    LEFT JOIN morph_genes g ON sm.gene_id=g.gene_id
    LEFT JOIN morph_combinations c ON s.species_id=c.species_id
    WHERE sm.morph_id IS NOT NULL OR c.combo_id IS NOT NULL
    GROUP BY s.species_id
    ORDER BY gene_cnt DESC
""").fetchall():
    print(f"  {row[0]:12s} {row[1]:3d}基因 {row[2]:3d}组合")

conn.close()
