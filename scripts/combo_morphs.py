#!/usr/bin/env python3
"""
combo_morphs.py — 经典组合品系种子数据生成器
将已知基因组合公式写入 morph_combinations 表
"""
import json, sqlite3, os

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
DB = os.path.join(DATA, 'digeguigui.db')

# ============================================
# 玉米蛇经典组合品系 (Corn Snake Combos)
# ============================================
CORN_COMBOS = [
    # 双基因
    ("Snow", "雪白", ["amelanistic", "anerythristic"], "Amelanistic + Anerythristic", "纯白底+粉红斑纹"),
    ("Blizzard", "暴风雪", ["amelanistic", "charcoal"], "Amelanistic + Charcoal", "纯白底+隐约黄纹"),
    ("Ghost", "幽灵", ["hypomelanistic", "anerythristic"], "Hypo + Anerythristic", "银灰底+灰纹，褪色效果"),
    ("Phantom", "幻影", ["hypomelanistic", "charcoal"], "Hypo + Charcoal", "淡灰底+紫灰纹"),
    ("Amber", "琥珀", ["hypomelanistic", "caramel"], "Hypo + Caramel", "金黄底+焦糖纹"),
    ("Butter", "黄油", ["amelanistic", "caramel"], "Amel + Caramel", "亮黄底+白纹"),
    ("Opal", "欧泊", ["amelanistic", "lavender"], "Amel + Lavender", "粉白底+淡紫纹"),
    ("Lavender Motley", "薰衣草圆点", ["lavender", "motley"], "Lavender + Motley", "紫灰底+圆点纹"),
    ("Plasma", "等离子", ["lavender", "diffused"], "Lavender + Bloodred", "深紫红底+扩散纹"),
    ("Pewter", "锡器", ["diffused", "charcoal"], "Bloodred + Charcoal", "银灰底+极简纹"),
    ("Granite", "花岗岩", ["diffused", "anerythristic"], "Bloodred + Anerythristic", "灰底+扩散纹"),
    ("Avalanche", "雪崩", ["diffused", "amelanistic"], "Bloodred + Amel", "白底+极淡红纹"),
    ("Hypo Lavender", "缺黑薰衣草", ["hypomelanistic", "lavender"], "Hypo + Lavender", "淡紫粉底"),
    ("Sunkissed Amel", "日吻白化", ["sunkissed", "amelanistic"], "Sunkissed + Amel", "鲜艳橙底"),
    ("Sunkissed Anery", "日吻缺红", ["sunkissed", "anerythristic"], "Sunkissed + Anery", "灰底+亮纹"),
    ("Sunkissed Caramel", "日吻焦糖", ["sunkissed", "caramel"], "Sunkissed + Caramel", "焦糖橙底"),
    ("Topaz", "托帕石", ["lava", "caramel"], "Lava + Caramel", "金黄橙底"),
    ("Ice", "冰", ["lava", "anerythristic"], "Lava + Anery", "冰蓝灰底"),
    ("Lava Lavender", "熔岩薰衣草", ["lava", "lavender"], "Lava + Lavender", "粉紫底+鲜艳纹"),
    ("Peppermint", "薄荷", ["cinder", "amelanistic"], "Cinder + Amel", "粉白底+淡粉纹"),
    ("Coral Snow", "珊瑚雪", ["amelanistic", "anerythristic", "hypomelanistic"], "Snow + Hypo", "粉白底+珊瑚粉纹"),
    ("Salmon Snow", "三文鱼雪", ["amelanistic", "anerythristic", "strawberry"], "Snow + Strawberry", "鲑鱼粉底"),
    ("Coral Ghost", "珊瑚幽灵", ["hypomelanistic", "anerythristic", "strawberry"], "Ghost + Strawberry", "粉灰底+珊瑚纹"),
    ("Orchid", "兰花", ["lavender", "sunkissed"], "Lavender + Sunkissed", "淡紫粉底+鲜艳纹"),
    # 三基因
    ("Honey", "蜂蜜", ["sunkissed", "caramel"], "Sunkissed + Caramel", "金黄蜜色"),
    ("Shatter", "碎裂", ["sunkissed", "cinder"], "Sunkissed + Cinder", "碎裂花纹"),
    ("Dilute Anery Motley", "稀释缺红圆点", ["dilute", "anerythristic", "motley"], "Dilute + Anery + Motley", "淡灰圆点"),
    ("Hypo Plasma", "缺黑等离子", ["hypomelanistic", "lavender", "diffused"], "Hypo + Plasma", "深粉扩散纹"),
    # Tessera 组合
    ("Tessera Snow", "镶嵌雪", ["tessera", "amelanistic", "anerythristic"], "Tessera + Snow", "白底+镶嵌背纹"),
    ("Tessera Blizzard", "镶嵌暴风雪", ["tessera", "amelanistic", "charcoal"], "Tessera + Blizzard", "白底+镶嵌纹"),
]

# ============================================
# 球蟒经典组合品系 (Ball Python Combos)
# ============================================
BALL_COMBOS = [
    # BEL (Blue-Eyed Leucistic) 系列
    ("Blue-Eyed Leucistic (Mojave)", "蓝眼白化·莫哈维", ["mojave", "lesser"], "Mojave + Lesser", "纯白蛇+蓝眼"),
    ("Blue-Eyed Leucistic (Mojavex2)", "蓝眼白化·双莫", ["mojave", "mojave"], "Super Mojave", "灰白底+蓝眼"),
    ("Blue-Eyed Leucistic (Lesserx2)", "蓝眼白化·双小丑", ["lesser", "lesser"], "Super Lesser", "纯白蛇+蓝眼"),
    
    # Black-Eyed Leucistic
    ("Black-Eyed Leucistic (Fire)", "黑眼白化·火", ["fire", "fire"], "Super Fire", "纯白蛇+黑眼"),
    
    # Ivory
    ("Ivory", "象牙", ["yellow_belly", "yellow_belly"], "Super Yellow Belly", "纯白蛇"),
    
    # 双基因经典
    
    ("Killer Bee", "杀人蜂", ["pastel", "spider"], "Super Pastel + Spider", "亮黄+蜘蛛纹"),
    ("Bumblebee", "大黄蜂", ["pastel", "spider"], "Pastel + Spider", "黄底+蜘蛛纹"),
    ("Killer Blast", "杀人爆破", ["pastel", "pastel", "pinstripe"], "Super Pastel + Pinstripe", "亮黄+直线纹"),
    ("Lemon Blast", "柠檬爆破", ["pastel", "pinstripe"], "Pastel + Pinstripe", "黄底+直线纹"),
    ("Jigsaw", "拼图", ["mojave", "pinstripe"], "Mojave + Pinstripe", "灰底+直线纹"),
    ("Pastave", "蜡笔莫哈维", ["pastel", "mojave"], "Pastel + Mojave", "黄灰渐变"),
    ("Banana Pastel", "香蕉蜡笔", ["banana", "pastel"], "Banana + Pastel", "鲜黄底"),
    ("Banana Mojave", "香蕉莫哈维", ["banana", "mojave"], "Banana + Mojave", "淡黄灰底"),
    ("Banana Spider", "香蕉蜘蛛", ["banana", "spider"], "Banana + Spider", "黄底+蜘蛛纹"),
    ("Banana Pinstripe", "香蕉直线", ["banana", "pinstripe"], "Banana + Pinstripe", "黄底+背纹"),
    ("Enchi Pastel", "恩奇蜡笔", ["enchi", "pastel"], "Enchi + Pastel", "橙底极简纹"),
    ("Enchi Mojave", "恩奇莫哈维", ["enchi", "mojave"], "Enchi + Mojave", "橙灰渐变"),
    ("Enchi Lesser", "恩奇小丑", ["enchi", "lesser"], "Enchi + Lesser", "淡橙底"),
    
    # 三基因
    ("Pastel Enchi Spider", "蜡笔恩奇蜘蛛", ["pastel", "enchi", "spider"], "Pastel + Enchi + Spider", "亮橙蜘蛛纹"),
    ("Pastel Enchi Pinstripe", "蜡笔恩奇直线", ["pastel", "enchi", "pinstripe"], "Pastel + Enchi + Pinstripe", "亮橙背纹"),
    ("Queen Bee", "女王蜂", ["pastel", "pastel", "spider", "lesser"], "Super Pastel + Spider + Lesser", "极亮黄+蜘蛛纹"),
    
    # 双隐性
    ("Albino Pied", "白化派", ["albino", "pied"], "Albino + Pied", "白底橙纹+白色区块"),
    ("Clown Pied", "小丑派", ["clown", "pied"], "Clown + Pied", "简纹+白色区块"),
    ("Genetic Stripe Pied", "基因直线派", ["genetic_stripe", "pied"], "G-Stripe + Pied", "背线+派白块"),
    
    # Super 形态
    ("Super Pastel", "超级蜡笔", ["pastel", "pastel"], "Super Pastel", "极亮黄+褪纹"),
    ("Super Cinnamon", "超级肉桂", ["cinnamon", "cinnamon"], "Super Cinnamon", "纯黑/深棕"),
    ("Super Enchi", "超级恩奇", ["enchi", "enchi"], "Super Enchi", "极简纹+橙底"),
    ("Super Vanilla", "超级香草", ["vanilla", "vanilla"], "Super Vanilla", "褪色淡黄"),
    ("Panda Pied", "熊猫派", ["cinnamon", "cinnamon", "pied"], "Super Cinnamon + Pied", "纯黑白熊猫色"),
]

# ============================================
# 豹纹守宫经典组合 (Leopard Gecko Combos)
# ============================================
GECKO_COMBOS = [
    ("Mack Snow Albino", "麦克斯诺白化", ["mack_snow", "tremper_albino"], "Mack Snow + Tremper Albino", "雪白粉底"),
    ("Super Snow", "超级雪", ["mack_snow", "mack_snow"], "Super Mack Snow", "纯黑白身+黑眼"),
    ("Super Snow Eclipse", "超级雪日食", ["mack_snow", "mack_snow", "eclipse"], "Super Snow + Eclipse", "纯白+全黑眼"),
    ("RADAR", "雷达", ["bell_albino", "eclipse"], "Bell Albino + Eclipse", "Bell白化+全黑眼"),
    ("RAPTOR", "猛禽", ["tremper_albino", "eclipse", "murphy_patternless"], "Tremper + Eclipse + Patternless", "橙身+红眼+无纹"),
    ("APTOR", "阿普托", ["tremper_albino", "murphy_patternless"], "Tremper + Patternless", "橙身+无纹"),
    ("Diablo Blanco", "迪亚波罗白", ["blizzard", "tremper_albino", "eclipse"], "Blizzard + Albino + Eclipse", "纯白+红眼"),
    ("Dreamsicle", "梦幻橙", ["enigma", "tremper_albino", "mack_snow"], "Enigma + Tremper + Mack Snow", "橙白迷幻纹"),
    ("Nova", "新星", ["enigma", "raptor"], "Enigma + RAPTOR", "高白侧+橙底"),
    ("Super Giant", "超级巨人", ["giant", "giant"], "Super Giant", "120g+巨头"),
    ("Tangerine Tornado", "橘化龙卷风", ["tangerine", "tremper_albino"], "Tangerine + Tremper", "浓橘无纹"),
    ("White & Yellow Tremper", "白黄 Tremper", ["white_yellow", "tremper_albino"], "W&Y + Tremper", "高白侧+橙底"),
    ("Eclipse Patternless", "日食无纹", ["eclipse", "murphy_patternless"], "Eclipse + Patternless", "全黑眼+纯色身"),
    ("Bell Blazing Blizzard", "Bell 烈火暴风雪", ["bell_albino", "blizzard"], "Bell Albino + Blizzard", "乳白无纹+淡红眼"),
]

combo_data = {
    "morphs_cornsnake.json": ("Pantherophis guttatus", CORN_COMBOS),
    "morphs_ballpython.json": ("Python regius", BALL_COMBOS),
    "morphs_leopardgecko.json": ("Eublepharis macularius", GECKO_COMBOS),
}

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Ensure gene_symbols exist in morph_genes
gene_lookup = {}
for row in cur.execute("SELECT gene_id, gene_symbol FROM morph_genes").fetchall():
    gene_lookup[row[1]] = row[0]

total_combos = 0
for fname, (species_latin, combos) in combo_data.items():
    sp = cur.execute("SELECT species_id, name_cn FROM species WHERE name_latin LIKE ?", (species_latin + '%',)).fetchone()
    if not sp:
        print(f"⚠️  Species not found: {species_latin}")
        continue
    
    print(f"\n🧬 {sp[1]} 组合品系导入...")
    for ename, cname, genes, formula, desc in combos:
        # Resolve gene_ids
        gene_ids = []
        for gsym in genes:
            if gsym in gene_lookup:
                gene_ids.append(gene_lookup[gsym])
            else:
                # Try inserting
                cur.execute("INSERT OR IGNORE INTO morph_genes (gene_symbol,gene_name,gene_name_cn,inheritance,is_proven) VALUES (?,?,?,'recessive',1)",
                    (gsym, gsym.replace('_', ' ').title(), ''))
                conn.commit()
                r = cur.execute("SELECT gene_id FROM morph_genes WHERE gene_symbol=?", (gsym,)).fetchone()
                if r:
                    gene_lookup[gsym] = r[0]
                    gene_ids.append(r[0])
        
        if not gene_ids:
            continue
        
        cur.execute("""
            INSERT OR IGNORE INTO morph_combinations 
            (species_id, combo_name, combo_name_cn, gene_ids, combo_formula, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            sp[0], ename, cname,
            json.dumps(gene_ids),
            formula, desc
        ))
        total_combos += 1

conn.commit()
print(f"\n✅ 总计导入: {total_combos} 个组合品系")

# Summary
for row in cur.execute("""
    SELECT s.name_cn, COUNT(mc.combo_id)
    FROM morph_combinations mc JOIN species s ON s.species_id=mc.species_id
    GROUP BY mc.species_id
""").fetchall():
    print(f"  {row[0]}: {row[1]} 组合")

conn.close()
