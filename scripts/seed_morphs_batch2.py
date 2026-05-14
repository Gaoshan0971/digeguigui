#!/usr/bin/env python3
"""seed_morphs_batch2.py — 第2批品系：猪鼻蛇/睫角/鬃狮/王蛇"""
import json, sqlite3, os

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'digeguigui.db')
conn = sqlite3.connect(DB)
cur = conn.cursor()

# ============================================================
# 1. 猪鼻蛇 Hognose (Heterodon nasicus) — 新星品系市场
# ============================================================
HOGNOSE_GENES = [
    ("albino","Albino","白化","recessive","color","T- Albino，鲜艳橙黄"),
    ("axanthic","Axanthic","缺黄","recessive","reduction","灰/银色调"),
    ("anaconda","Anaconda","森蚺纹","incomplete_dominant","pattern","减少斑纹，超级形态=Superconda(无纹)"),
    ("arctic","Arctic","北极","incomplete_dominant","color","高对比度，超级=Super Arctic(近乎纯白+黑斑)"),
    ("toffee_belly","Toffee Belly","太妃糖腹","recessive","color","焦糖色腹部+绿色调"),
    ("lavender","Lavender","薰衣草","recessive","color","紫色调，稀有高端品系"),
    ("caramel","Caramel","焦糖","recessive","color","焦糖色调"),
    ("sable","Sable","黑貂","incomplete_dominant","color","暗化基因，超级=几近纯黑"),
    ("leucistic","Leucistic","白变","recessive","color","纯白蛇蓝眼/黑眼,极度稀有"),
    ("pink_pastel","Pink Pastel","粉蜡笔","polygenic","color","粉色调，线育品系"),
    ("red","Red","红系","polygenic","color","深红色调"), 
    ("purple_line","Purple Line","紫线","polygenic","color","深紫色线育"),
    ("green_phase","Green Phase","绿相","polygenic","color","绿色调"),
    ("twinspot","Twinspot","双斑","recessive","pattern","背部双排斑点"),
    ("lemon_ghost","Lemon Ghost","柠檬幽灵","recessive","color","淡黄色调"),
    ("stormcloud","Stormcloud","暴风云","recessive","color","暗灰蓝调 稀有"),
    ("swiss_chocolate","Swiss Chocolate","瑞士巧克力","recessive","color","巧克力棕"),
    ("yeti","Yeti","雪人","incomplete_dominant","color","白底+淡纹 超级纯白"),
    ("jaguar","Jaguar","美洲豹","recessive","pattern","特殊斑纹"),
    ("moonglow","Moonglow","月光","recessive","color","淡粉白 稀有组合基础"),
]

HOGNOSE_COMBOS = [
    ("Super Arctic","超级北极",["arctic","arctic"],"Super Arctic","纯白底+黑斑 标志性品系"),
    ("Superconda","超级森蚺",["anaconda","anaconda"],"Super Anaconda","纯色无纹 标志性品系"),
    ("Toffeebelly","太妃糖",["toffee_belly","toffee_belly"],"Visual Toffee Belly","焦糖腹+绿色"),
    ("Toxic","毒液",["toffee_belly","axanthic"],"Toffee Belly + Axanthic","银灰+绿调 热门"),
    ("Arctic Toffee","北极太妃",["arctic","toffee_belly"],"Arctic + Toffee Belly","高对比+绿调"),
    ("Albino Anaconda","白化森蚺",["albino","anaconda"],"Albino + Anaconda","橙黄+简纹"),
    ("Snow","雪",["albino","axanthic"],"Albino + Axanthic","粉白+淡纹"),
    ("Lavender Anaconda","薰衣草森蚺",["lavender","anaconda"],"Lavender + Anaconda","紫色+简纹"),
    ("Arctic Albino","北极白化",["arctic","albino"],"Arctic + Albino","高对比橙黄"),
    ("Super Arctic Albino","超级北极白化",["arctic","arctic","albino"],"Super Arctic + Albino","纯白+粉斑 legend级"),
    ("Super Arctic Superconda","超北极超森蚺",["arctic","arctic","anaconda","anaconda"],"Super Arctic + Superconda","纯白无纹 天花板"),
    ("Pink Pastel Anaconda","粉蜡笔森蚺",["pink_pastel","anaconda"],"Pink Pastel + Anaconda","粉色+简纹"),
    ("Sable Anaconda","黑貂森蚺",["sable","anaconda"],"Sable + Anaconda","暗色+简纹"),
    ("Leucistic Arctic","白变北极",["leucistic","arctic"],"Leucistic + Arctic","超白高对比"),
    ("Moonglow Arctic","月光北极",["moonglow","arctic"],"Moonglow + Arctic","冰蓝色调"),
]

# ============================================================
# 2. 睫角守宫 Crested Gecko (Correlophus ciliatus)
# ============================================================
CRESTED_GENES = [
    ("lily_white","Lily White","百合白","incomplete_dominant","pattern","高白侧壁，超级=超高白"),
    ("axanthic","Axanthic","缺黄","recessive","reduction","灰/棕色调"),
    ("patternless","Patternless","无纹","recessive","pattern","纯色无纹"),
    ("pinstripe","Pinstripe","细纹","dominant","pattern","背部细纹"),
    ("phantom","Phantom","幻影","recessive","pattern","淡化纹路"),
    ("soft_scale","Soft Scale","软鳞","recessive","scale","细嫩鳞片"),
    ("cappuccino","Cappuccino","卡布奇诺","incomplete_dominant","color","棕褐调 超级淡色"),
    ("moonglow","Moonglow","月光","recessive","color","淡白发光"),
    ("brindle","Brindle","虎斑","recessive","pattern","不规则条纹"),
    ("quad_stripe","Quad Stripe","四线","polygenic","pattern","四条完整背线"),
    ("dalmatian","Dalmatian","斑点","dominant","pattern","黑/红斑点数可叠加"),
    ("harlequin","Harlequin","花斑","polygenic","pattern","高花纹覆盖率"),
    ("flame","Flame","火焰","polygenic","color","背脊火焰纹"),
    ("tricolor","Tricolor","三色","polygenic","color","三色分布"),
]

CRESTED_COMBOS = [
    ("Lily White Pinstripe","百合白细纹",["lily_white","pinstripe"],"Lily White + Pinstripe","高白+背纹"),
    ("Lily White Dalmatian","百合白斑点",["lily_white","dalmatian"],"Lily White + Dalmatian","高白+密集斑点"),
    ("Super Lily White","超级百合白",["lily_white","lily_white"],"Super Lily White","极高白色覆盖"),
    ("Axanthic Lily White","缺黄百合白",["axanthic","lily_white"],"Axanthic + Lily White","灰白调"),
    ("Phantom Pinstripe","幻影细纹",["phantom","pinstripe"],"Phantom + Pinstripe","淡化+细纹"),
    ("Dalmatian Harlequin","斑点花斑",["dalmatian","harlequin"],"Dalmatian + Harlequin","密集斑点+花纹"),
    ("Cappuccino Lily White","卡布百合",["cappuccino","lily_white"],"Cappuccino + Lily White","棕白调"),
    ("Quad Stripe Pinstripe","四线细纹",["quad_stripe","pinstripe"],"Quad Stripe + Pinstripe","四线+细纹"),
    ("Moonglow Phantom","月光幻影",["moonglow","phantom"],"Moonglow + Phantom","淡白光+淡化纹"),
    ("Super Dalmatian","超级斑点",["dalmatian","dalmatian"],"Super Dalmatian (line-bred)","100+斑点数"),
]

# ============================================================
# 3. 鬃狮蜥 Bearded Dragon (Pogona vitticeps)
# ============================================================
BEARDED_GENES = [
    ("hypo","Hypomelanistic","缺黑","recessive","reduction","透明爪，浅色体"),
    ("translucent","Translucent","透鳞","recessive","scale","半透明鳞片，黑眼"),
    ("leatherback","Leatherback","革背","codominant","scale","小棘刺减少，超级=Silkie(无棘刺)"),
    ("dunner","Dunner","丹纳鳞","dominant","scale","鳞片反向生长，粗狂质感"),
    ("zero","Zero","零纹","recessive","pattern","纯色无纹，银灰/纯白/纯黑品系"),
    ("witblits","Witblits","白闪","recessive","pattern","南非无纹品系，淡色无纹"),
    ("wero","Wero","维罗","recessive","pattern","Zero x Witblits组合型无纹"),
    ("paradox","Paradox","悖论","unknown","pattern","随机色斑分布，不可预测"),
    ("red_monster","Red Monster","红怪","polygenic","color","深红/血红线育"),
    ("citrus","Citrus","柑橘","polygenic","color","鲜黄/橙线育"),
    ("orange","Orange","橙系","polygenic","color","橙色线育"),
    ("purple","Purple","紫系","polygenic","color","紫色调线育"),
    ("blue_bar","Blue Bar","蓝条","polygenic","color","蓝色侧斑"),
]

BEARDED_COMBOS = [
    ("Silkie","丝绒",["leatherback","leatherback"],"Super Leatherback","无棘刺光滑体表"),
    ("Zero Leatherback","零纹革背",["zero","leatherback"],"Zero + Leatherback","无纹+革背"),
    ("Zero Hypo Trans","零纹缺黑透",["zero","hypo","translucent"],"Zero + Hypo + Trans","纯色无纹+透明鳞"),
    ("Red Monster Leatherback","红怪革背",["red_monster","leatherback"],"Red Monster + Leatherback","血红+革背"),
    ("Citrus Hypo Trans","柑橘缺黑透",["citrus","hypo","translucent"],"Citrus + Hypo + Trans","鲜黄+透明爪+透明鳞"),
    ("Paradox Zero","悖论零纹",["paradox","zero"],"Paradox + Zero","随机色斑+无纹"),
    ("Dunner Leatherback","丹纳革背",["dunner","leatherback"],"Dunner + Leatherback","粗狂+简刺"),
    ("Witblits Hypo","白闪缺黑",["witblits","hypo"],"Witblits + Hypo","白调+透明爪"),
    ("Purple Zero","紫零纹",["purple","zero"],"Purple + Zero","紫色调+无纹"),
    ("Blue Bar Hypo","蓝条缺黑",["blue_bar","hypo"],"Blue Bar + Hypo","蓝侧斑+淡色"),
    ("Orange Citrus Leatherback","橙柑橘革背",["orange","citrus","leatherback"],"Orange + Citrus + Leatherback","鲜橙色简刺"),
]

# ============================================================
# 4. 王蛇系 King/Milk Snakes (Lampropeltis)
# ============================================================
KINGSNAKE_GENES = [
    ("albino","Albino","白化","recessive","color","T- Albino"),
    ("hyper_melanistic","Hyper Melanistic","超黑","recessive","color","乌黑体色"),
    ("striped","Striped","直线","recessive","pattern","背部贯通直线"),
    ("patternless","Patternless","无纹","recessive","pattern","纯色无纹"),
    ("mosaic","Mosaic","马赛克","recessive","pattern","碎裂花纹"),
    ("hypo","Hypomelanistic","缺黑","recessive","reduction","淡化体色"),
    ("lavender","Lavender Albino","薰衣草白化","recessive","color","紫色调白化"),
    ("peanut_butter","Peanut Butter","花生酱","recessive","color","黄棕调"),
    ("white_sided","White Sided","白侧","recessive","pattern","侧腹白色"),
    ("axanthic","Axanthic","缺黄","recessive","reduction","灰/银色调"),
    ("ghost","Ghost","幽灵","recessive","color","Hypo + Axanthic 组合型，银灰调"),
]

KINGSNAKE_COMBOS = [
    ("Albino Striped","白化直线",["albino","striped"],"Albino + Striped","橙黄底+白直线"),
    ("Hyper Mel Striped","超黑直线",["hyper_melanistic","striped"],"Hyper Mel + Striped","乌黑+白直线"),
    ("Albino White-Sided","白化白侧",["albino","white_sided"],"Albino + White-Sided","白化+白侧"),
    ("Ghost Striped","幽灵直线",["ghost","striped"],"Ghost + Striped","银灰+直线"),
    ("Lavender Striped","薰衣草直线",["lavender","striped"],"Lavender Albino + Striped","紫色调+直线"),
    ("Mosaic Striped","马赛克直线",["mosaic","striped"],"Mosaic + Striped","碎裂花纹+直线"),
    ("Peanut Butter Albino","花生酱白化",["peanut_butter","albino"],"Peanut Butter + Albino","黄棕+白化"),
]

# ============================================================
# 写入数据库
# ============================================================

SPECIES_MAP = {
    "Heterodon nasicus": ("猪鼻蛇", HOGNOSE_GENES, HOGNOSE_COMBOS),
    "Correlophus ciliatus": ("睫角守宫", CRESTED_GENES, CRESTED_COMBOS),
    "Pogona vitticeps": ("鬃狮蜥", BEARDED_GENES, BEARDED_COMBOS),
    "Lampropeltis getula": ("王蛇系", KINGSNAKE_GENES, KINGSNAKE_COMBOS),
}

insGene = "INSERT OR IGNORE INTO morph_genes (gene_symbol,gene_name,gene_name_cn,inheritance,category,description,is_proven) VALUES (?,?,?,?,?,?,1)"
insMorph = "INSERT OR IGNORE INTO species_morphs (species_id,gene_id,morph_name,morph_name_cn,is_base_morph) VALUES (?,?,?,?,1)"
insCombo = "INSERT OR IGNORE INTO morph_combinations (species_id,combo_name,combo_name_cn,gene_ids,combo_formula,description) VALUES (?,?,?,?,?,?)"

total_genes = total_combos = 0

for latin, (cn_name, genes, combos) in SPECIES_MAP.items():
    sp = cur.execute("SELECT species_id, name_cn FROM species WHERE name_latin LIKE ? LIMIT 1", (latin + '%',)).fetchone()
    if not sp:
        print(f"⚠️ 物种未找到: {latin}")
        continue
    
    sp_id, sp_cn = sp
    print(f"\n🧬 {cn_name} (id={sp_id}) — {len(genes)}基因 + {len(combos)}组合")

    # Insert genes
    for g in genes:
        sym, name, cn, inherit, cat, desc = g[:6]
        cur.execute(insGene, (sym, name, cn, inherit, cat, desc))
        gene_row = cur.execute("SELECT gene_id FROM morph_genes WHERE gene_symbol=?", (sym,)).fetchone()
        if gene_row:
            cur.execute(insMorph, (sp_id, gene_row[0], name, cn))
            total_genes += 1

    # Insert combos
    gene_lookup = {r[1]: r[0] for r in cur.execute("SELECT gene_id, gene_symbol FROM morph_genes")}
    for c in combos:
        ename, cname, genes_list, formula, desc = c[:5]
        gene_ids = []
        for gsym in genes_list:
            if gsym in gene_lookup:
                gene_ids.append(gene_lookup[gsym])
        if gene_ids:
            cur.execute(insCombo, (sp_id, ename, cname, json.dumps(gene_ids), formula, desc))
            total_combos += 1

conn.commit()

# Summary
cur.execute("""
    SELECT s.name_cn, COUNT(DISTINCT sm.morph_id) as genes, COUNT(DISTINCT mc.combo_id) as combos
    FROM species s
    LEFT JOIN species_morphs sm ON s.species_id=sm.species_id
    LEFT JOIN morph_combinations mc ON s.species_id=mc.species_id
    GROUP BY s.species_id
    HAVING genes > 0 OR combos > 0
    ORDER BY genes DESC
""")
print("\n📊 品系覆盖品种:")
for r in cur.fetchall():
    print(f"  {r[0]:12s} {r[1]:3d}基因  {r[2]:3d}组合")

print(f"\n总计: {cur.execute('SELECT COUNT(*) FROM morph_genes').fetchone()[0]}基因 | {cur.execute('SELECT COUNT(*) FROM morph_combinations').fetchone()[0]}组合")

conn.close()
