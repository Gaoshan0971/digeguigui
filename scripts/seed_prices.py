#!/usr/bin/env python3
"""
seed_prices.py — 爬宠异宠市场价格数据库
种子数据来源：国内爬圈行情（2026估算）+ MorphMarket参考
RMB计价，三级精度：普通/优选/极品
"""
import sqlite3, json

DB = '/home/ubuntu/digeguigui/data/digeguigui.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# 建价格表
cur.executescript("""
CREATE TABLE IF NOT EXISTS species_prices (
    price_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    species_id  INTEGER NOT NULL UNIQUE,
    normal_low  REAL NOT NULL DEFAULT 0,     -- 普通个体低价
    normal_high REAL NOT NULL DEFAULT 0,     -- 普通个体高价
    select_low  REAL NOT NULL DEFAULT 0,     -- 优选个体低价
    select_high REAL NOT NULL DEFAULT 0,     -- 优选个体高价  
    premium_low REAL NOT NULL DEFAULT 0,     -- 极品个体低价
    premium_high REAL NOT NULL DEFAULT 0,    -- 极品个体高价
    currency    TEXT DEFAULT 'CNY',
    price_note  TEXT DEFAULT '',
    updated_at  TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (species_id) REFERENCES species(species_id)
);

CREATE TABLE IF NOT EXISTS morph_prices (
    price_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    species_id      INTEGER NOT NULL,
    gene_id         INTEGER,                 -- NULL = combo
    combo_id        INTEGER,                 -- NULL = single gene
    het_price       REAL DEFAULT NULL,       -- het/杂合价格
    visual_price    REAL DEFAULT NULL,       -- 纯合表现价格
    super_price     REAL DEFAULT NULL,       -- 超级形态价格
    price_range_low REAL DEFAULT NULL,       -- 价格区间低
    price_range_high REAL DEFAULT NULL,      -- 价格区间高
    currency        TEXT DEFAULT 'CNY',
    rarity          TEXT DEFAULT 'common',   -- common/uncommon/rare/ultra_rare/legendary
    price_note      TEXT DEFAULT '',
    updated_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (species_id) REFERENCES species(species_id),
    FOREIGN KEY (gene_id) REFERENCES morph_genes(gene_id),
    FOREIGN KEY (combo_id) REFERENCES morph_combinations(combo_id)
);

CREATE INDEX IF NOT EXISTS idx_price_species ON species_prices(species_id);
CREATE INDEX IF NOT EXISTS idx_morph_price_species ON morph_prices(species_id);
""")
conn.commit()

# ============================================================
# 一、物种基础价格（按品类 x 热度）
# ============================================================
SPECIES_PRICES = {
    # ===== 蛇类热门 =====
    448: (200, 400, 500, 1000, 1500, 5000, "玉米蛇 普通200-400 品系见morph表"),
    457: (300, 600, 800, 2000, 3000, 10000, "球蟒 普通300-600 品系见morph表"),
    452: (400, 800, 1000, 2000, 3000, 8000, "猪鼻蛇 北极/白化类溢价高"),
    449: (200, 500, 600, 1500, 2000, 5000, "王蛇 白化/直线类品系多"),
    451: (200, 500, 600, 1200, 2000, 5000, "奶蛇 morph品系溢价"),
    507: (300, 600, 800, 1500, 2000, 5000, "红尾蚺/中美蚺"),
    509: (500, 1000, 1500, 3000, 5000, 10000, "缅甸蟒 白化/迷宫类溢价"),
    508: (800, 1500, 2000, 4000, 5000, 15000, "网纹蟒 大型蟒需专业饲养"),
    505: (600, 1200, 1500, 3000, 4000, 10000, "地毯蟒"),
    504: (500, 1000, 1200, 2500, 3000, 8000, "血蟒/短尾蟒"),
    510: (800, 2000, 2500, 5000, 5000, 15000, "绿树蟒"),
    # ===== 蜥蜴热门 =====
    459: (100, 300, 400, 1000, 1500, 5000, "鬃狮蜥 品系溢价高 leatherback/silkie/zero"),
    462: (100, 300, 300, 600, 600, 1500, "绿鬣蜥 普通100-300 蓝/红变异贵"),
    474: (300, 600, 800, 1500, 1500, 3000, "高冠变色龙"),
    482: (300, 800, 1000, 2000, 2000, 5000, "七彩变色龙"),
    # ===== 守宫热门 =====
    458: (50, 150, 200, 500, 800, 3000, "豹纹守宫 品系见morph表"),
    461: (150, 400, 500, 1500, 2000, 5000, "睫角守宫 品系溢价高"),
    463: (200, 500, 600, 1500, 2000, 4000, "肥尾守宫"),
    465: (1000, 3000, 3000, 6000, 6000, 15000, "巨人守宫"),
    # ===== 龟类热门 =====
    # (已在前端有价格体系的龟类暂略，重点异宠)
    1: (10, 30, 50, 100, 100, 200, "巴西龟"),
    2: (30, 80, 100, 200, 200, 500, "草龟"),
    3: (50, 150, 200, 400, 400, 1000, "花龟"),
    30: (100, 300, 400, 800, 800, 2000, "剃刀龟"),
    31: (80, 200, 300, 600, 600, 1500, "麝香龟"),
    40: (300, 800, 1000, 2000, 3000, 8000, "红腿陆龟"),
    41: (500, 1500, 2000, 5000, 5000, 15000, "苏卡达陆龟 幼体500-1500 成体按斤"),
    35: (50, 150, 200, 400, 400, 1000, "黄耳龟"),
    # ===== 蛙类热门 =====
    577: (100, 300, 400, 800, 800, 2000, "角蛙"),
    590: (150, 400, 500, 1000, 1500, 3000, "老爷树蛙"),
    591: (200, 500, 600, 1200, 1200, 3000, "番茄蛙"),
    603: (100, 300, 400, 800, 800, 2000, "非洲牛蛙"),
    # 箭毒蛙
    594: (200, 500, 600, 1200, 1200, 3000, "钴蓝箭毒蛙"),
    595: (300, 800, 1000, 2000, 2000, 5000, "金色箭毒蛙"),
}

# ============================================================
# 二、品系价格数据（按物种 x 基因 x 组合）
# ============================================================
MORPH_PRICES = {
    # --- 玉米蛇 ---
    "amelanistic":        (300, 600, 200, 400, None, "白化 经典入门品系 common"),
    "anerythristic":      (300, 600, 200, 400, None, "缺红A型 common"),
    "hypomelanistic":     (300, 600, 200, 400, None, "缺黑 common"),
    "caramel":            (400, 800, 300, 500, None, "焦糖 uncommon"),
    "lavender":           (600, 1200, 400, 800, None, "薰衣草 uncommon"),
    "charcoal":           (400, 800, 300, 600, None, "缺红B uncommon"),
    "diffused":           (500, 1000, 400, 700, None, "扩散/血红 uncommon"),
    "motley":             (300, 600, 200, 400, None, "圆点纹 common"),
    "stripe":             (400, 800, 300, 500, None, "直线纹 uncommon"),
    "tessera":            (800, 2000, 600, 1200, None, "镶嵌 dominant 溢价高"),
    "scaleless":          (1000, 3000, 800, 2000, None, "无鳞 rare"),
    "lava":               (500, 1000, 400, 700, None, "熔岩 uncommon"),
    "sunkissed":          (600, 1200, 400, 800, None, "日吻 uncommon"),
    "ultra":              (500, 1000, 300, 600, None, "超白 codominant uncommon"),
    "cinder":             (600, 1200, 400, 800, None, "灰烬 uncommon"),
    "dilute":             (600, 1500, 500, 1000, None, "稀释 rare"),
    "palmetto":           (5000, 15000, 3000, 8000, None, "棕榈 ultra_rare 价格极高"),
    "pied_sided":         (1500, 4000, 1000, 2500, None, "侧派 rare"),
    "toffee":             (1000, 3000, 800, 2000, None, "太妃糖 rare"),
    "buf":                (800, 2000, 600, 1500, None, "水牛皮 uncommon"),
    "masque":             (400, 800, 300, 600, None, "面具 uncommon"),
    "strawberry":         (800, 2000, 600, 1500, None, "草莓 uncommon"),
    # 玉米蛇组合
    "Snow":               (1500, 4000, "Amel+Anery 雪白 经典组合 common"),
    "Blizzard":           (1500, 4000, "Amel+Charcoal 暴风雪 uncommon"),
    "Ghost":              (1000, 2500, "Hypo+Anery 幽灵 uncommon"),
    "Butter":             (1200, 3000, "Amel+Caramel 黄油 uncommon"),
    "Pewter":             (2000, 5000, "Bloodred+Charcoal 锡器 rare"),
    "Plasma":             (2000, 5000, "Lavender+Bloodred 等离子 rare"),
    "Opal":               (1500, 4000, "Amel+Lavender 欧泊 uncommon"),
    "Granite":            (1500, 4000, "Bloodred+Anery 花岗岩 uncommon"),
    "Avalanche":          (2000, 5000, "Bloodred+Amel 雪崩 rare"),
    "Honey":              (2000, 5000, "Sunkissed+Caramel 蜂蜜 rare"),
    "Coral Snow":         (3000, 8000, "Snow+Hypo 珊瑚雪 rare"),
    "Salmon Snow":        (3000, 10000, "Snow+Strawberry 三文鱼雪 rare"),
    
    # --- 球蟒 ---
    "pastel":             (600, 1200, 400, 800, None, "蜡笔 codominant common"),
    "spider":             (500, 1000, None, None, None, "蜘蛛 dominant common"),
    "pinstripe":          (500, 1000, None, None, None, "直线 dominant common"),
    "mojave":             (600, 1200, 400, 800, None, "莫哈维 codominant common"),
    "lesser":             (600, 1200, 400, 800, None, "小丑/黄油 codominant common"),
    "banana":             (1000, 2000, 600, 1200, None, "香蕉 codominant uncommon"),
    "enchi":              (500, 1000, 300, 700, None, "恩奇 codominant common"),
    "cinnamon":           (500, 1000, 300, 700, None, "肉桂 codominant common"),
    "black_pastel":       (500, 1200, 300, 800, None, "黑蜡笔 codominant common"),
    "fire":               (500, 1000, 300, 700, None, "火 codominant common"),
    "yellow_belly":       (300, 600, 200, 400, None, "黄腹 codominant common"),
    "vanilla":            (500, 1000, 300, 700, None, "香草 codominant uncommon"),
    "calico":             (800, 2000, 500, 1200, None, "印花 codominant uncommon"),
    "champagne":          (600, 1500, None, None, None, "香槟 dominant uncommon"),
    "orange_dream":       (800, 2000, 500, 1200, None, "橙梦 codominant uncommon"),
    "leopard":            (600, 1500, 400, 1000, None, "豹纹 codominant uncommon"),
    "bamboo":             (800, 2000, 500, 1200, None, "竹子 codominant uncommon"),
    "mahogany":           (800, 2000, 500, 1200, None, "红木 codominant uncommon"),
    "ghi":                (1000, 2500, 600, 1500, None, "GHI codominant rare"),
    "albino":             (800, 2000, 500, 1200, None, "白化 recessive uncommon"),
    "pied":               (2000, 5000, 1000, 3000, None, "派 recessive rare"),
    "clown":              (3000, 8000, 1500, 4000, None, "小丑 recessive rare 价格持续攀升"),
    "axanthic":           (1000, 2500, 600, 1500, None, "缺黄 recessive uncommon"),
    "genetic_stripe":     (1500, 4000, 800, 2000, None, "基因直线 recessive rare"),
    "ghost":              (800, 2000, 500, 1200, None, "幽灵 recessive uncommon"),
    "caramel_albino":     (1000, 2500, 600, 1500, None, "焦糖白化 recessive uncommon"),
    "lavender_albino":    (2000, 5000, 1000, 3000, None, "薰衣草白化 recessive rare"),
    "desert_ghost":       (2000, 5000, 1000, 3000, None, "沙漠幽灵 incomplete_dominant rare"),
    # 球蟒组合
    "Killer Bee":         (3000, 8000, "Super Pastel+Spider 杀人蜂 rare"),
    "Bumblebee":          (1500, 3000, "Pastel+Spider 大黄蜂 uncommon"),
    "Lemon Blast":        (1500, 3000, "Pastel+Pinstripe 柠檬爆破 uncommon"),
    "Blue-Eyed Leucistic (Mojave)": (8000, 20000, "Mojave+Lesser BEL 蓝眼白化 rare 价格高"),
    "Black-Eyed Leucistic (Fire)":  (6000, 15000, "Super Fire 黑眼白化 rare"),
    "Ivory":              (3000, 8000, "Super Yellow Belly 象牙 uncommon"),
    "Panda Pied":         (20000, 80000, "Super Cinnamon+Pied 熊猫派 legend"),
    "Jigsaw":             (1500, 4000, "Mojave+Pinstripe 拼图 uncommon"),
    "Pastave":            (1500, 3000, "Pastel+Mojave 蜡笔莫哈维 uncommon"),
    "Albino Pied":        (8000, 20000, "Albino+Pied 白化派 rare"),
    "Clown Pied":         (20000, 50000, "Clown+Pied 小丑派 legend"),
    
    # --- 豹纹守宫 ---
    "tremper_albino":     (200, 500, 100, 300, None, "Tremper白化 common"),
    "bell_albino":        (300, 600, 150, 400, None, "Bell白化 uncommon"),
    "rainwater_albino":   (200, 500, 100, 300, None, "雨水白化 common"),
    "murphy_patternless": (300, 600, 150, 400, None, "无纹 uncommon"),
    "blizzard":           (400, 800, 200, 500, None, "暴风雪 uncommon"),
    "eclipse":            (400, 1000, 200, 600, None, "日食 uncommon"),
    "mack_snow":          (300, 600, 150, 400, None, "麦克斯诺 codominant common"),
    "giant":              (400, 800, 200, 500, None, "巨人 codominant uncommon"),
    "enigma":             (300, 600, None, None, None, "谜 dominant common 有神经问题风险"),
    "white_yellow":       (500, 1200, None, None, None, "白黄 dominant uncommon"),
    "tangerine":          (300, 1000, "橘化 polygenic 深橘+溢价"),
    # 守宫组合
    "Super Snow":         (800, 2000, "Super Mack Snow 超级雪 uncommon"),
    "RAPTOR":             (1000, 3000, "Tremper+Eclipse+Patternless 猛禽 rare"),
    "Diablo Blanco":      (1500, 4000, "Blizzard+Albino+Eclipse 纯白红眼 rare"),
    "Super Giant":        (1500, 4000, "Super Giant 超级巨人 uncommon"),
    "Super Snow Eclipse": (2000, 5000, "Super Snow+Eclipse 纯白全黑眼 rare"),
}

# ============================================================
# 三、写入
# ============================================================

# 物种价格
for sid, (nl, nh, sl, sh, pl, ph, note) in SPECIES_PRICES.items():
    cur.execute("""
        INSERT OR REPLACE INTO species_prices (species_id, normal_low, normal_high, select_low, select_high, premium_low, premium_high, price_note)
        VALUES (?,?,?,?,?,?,?,?)
    """, (sid, nl, nh, sl, sh, pl, ph, note))
print(f"✅ 物种价格: {len(SPECIES_PRICES)} 种")

# 品系价格
gene_prices = 0
combo_prices = 0

for symbol, value in MORPH_PRICES.items():
    if len(value) == 6:  # gene: het_low, het_high, vis_low, vis_high, super_low, note
        hl, hh, vl, vh, sl, note = value
        # Find gene_id and species
        gene = cur.execute("SELECT g.gene_id, sm.species_id FROM morph_genes g JOIN species_morphs sm ON g.gene_id=sm.gene_id WHERE g.gene_symbol=?", (symbol,)).fetchone()
        if gene:
            het_avg = (hl+hh)//2 if hl and hh else hl or hh or 0
            vis_avg = (vl+vh)//2 if vl and vh else vl or vh or 0
            sp = sl or None
            rarity = note.split()[-1] if note and ' ' in note else 'common'
            if rarity not in ('common','uncommon','rare','ultra_rare','legendary'):
                rarity = 'common'
            cur.execute("""
                INSERT INTO morph_prices (species_id, gene_id, het_price, visual_price, super_price, price_range_low, price_range_high, rarity, price_note)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (gene[1], gene[0], het_avg, vis_avg, sp, hl, vh, rarity, note))
            gene_prices += 1
    elif len(value) == 3:  # combo: price_low, price_high, note
        pl, ph, note = value
        combo = cur.execute("SELECT c.combo_id, c.species_id FROM morph_combinations c WHERE c.combo_name=?", (symbol,)).fetchone()
        if combo:
            rarity = 'rare'
            for r in ['legend','ultra_rare','rare','uncommon','common']:
                if r in note.lower():
                    rarity = r.replace('_',' ')
                    break
            cur.execute("""
                INSERT INTO morph_prices (species_id, combo_id, price_range_low, price_range_high, rarity, price_note)
                VALUES (?,?,?,?,?,?)
            """, (combo[1], combo[0], pl, ph, rarity, note))
            combo_prices += 1

conn.commit()
print(f"✅ 基因价格: {gene_prices} 条")
print(f"✅ 组合价格: {combo_prices} 条")

# Stats
total_species_price = cur.execute("SELECT COUNT(*) FROM species_prices").fetchone()[0]
total_morph_price = cur.execute("SELECT COUNT(*) FROM morph_prices").fetchone()[0]
print(f"\n📊 价格数据库: {total_species_price} 物种 + {total_morph_price} 品系")

conn.close()
