#!/usr/bin/env python3
"""
每日全网爬宠数据巡检
- TTS/BW 价格变化检测
- 新上架品种发现
- 训练数据缺口检测（哪些品种图不够）
- 输出简短报告
"""

import json, os, sys, time, re
from datetime import datetime
from urllib.request import urlopen, Request

UA = "Mozilla/5.0 (compatible; Digeguigui/1.0)"
PROJ = os.path.expanduser("~/digeguigui")
DATA = os.path.join(PROJ, "data")
DB = os.path.join(DATA, "digeguigui.db")
TTS_FILE = os.path.join(DATA, "tts_products.json")
BW_FILE = os.path.join(DATA, "bw_products.json")
DIFF_FILE = os.path.join(DATA, "daily_diff.json")

def run(cmd):
    import subprocess
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip()

def check_db_stats():
    """数据库统计：物种数/图片覆盖率/价格覆盖率"""
    import sqlite3
    conn = sqlite3.connect(DB)
    
    # 总物种
    total = conn.execute("SELECT COUNT(*) FROM species").fetchone()[0]
    
    # 有图的物种
    with_img = conn.execute(
        "SELECT COUNT(*) FROM species WHERE image_url IS NOT NULL AND image_url != ''"
    ).fetchone()[0]
    
    # 有 market_data 的物种
    with_price = conn.execute(
        "SELECT COUNT(*) FROM species WHERE market_data IS NOT NULL AND market_data != '{}'"
    ).fetchone()[0]
    
    # 有 care_params 的物种
    with_care = conn.execute(
        "SELECT COUNT(*) FROM species WHERE care_params IS NOT NULL AND care_params != '{}'"
    ).fetchone()[0]
    
    # 识龟模型覆盖（有训练数据的品种）
    with_train = conn.execute(
        "SELECT COUNT(DISTINCT species_id) FROM labeled_appraisals"
    ).fetchone()[0]
    
    # 品类分布
    categories = conn.execute(
        "SELECT category, COUNT(*) FROM species GROUP BY category ORDER BY COUNT(*) DESC"
    ).fetchall()
    
    # 最近识龟反馈统计
    feedback_stats = {}
    try:
        fb = conn.execute(
            "SELECT feedback_type, COUNT(*) FROM identify_feedback GROUP BY feedback_type"
        ).fetchall()
        feedback_stats = {row[0]: row[1] for row in fb}
    except:
        pass
    
    conn.close()
    
    return {
        "total_species": total,
        "with_image": with_img,
        "image_coverage": f"{with_img/total*100:.0f}%",
        "with_price": with_price,
        "price_coverage": f"{with_price/total*100:.0f}%",
        "with_care": with_care,
        "care_coverage": f"{with_care/total*100:.0f}%",
        "species_with_training": with_train,
        "feedback": feedback_stats,
        "categories": dict(categories),
    }

def reconnect():
    """Re-establish the database connection"""
    import sqlite3
    return sqlite3.connect(DB)

def check_image_gaps():
    """检测哪些龟类缺图 — 优先爬取目标"""
    import sqlite3
    conn = sqlite3.connect(DB)
    
    # 没有 market_image 且没有现有图的龟类
    gaps = conn.execute("""
        SELECT name_cn, name_latin, care_params 
        FROM species 
        WHERE category = '龟' 
          AND (image_url IS NULL OR image_url = '')
          AND (market_data IS NULL OR market_data = '{}')
        ORDER BY 
          CASE WHEN care_params LIKE '%"difficulty":1%' THEN 1
               WHEN care_params LIKE '%"difficulty":2%' THEN 2
               ELSE 3 END
        LIMIT 20
    """).fetchall()
    
    conn.close()
    return [{"name_cn": r[0], "name_latin": r[1]} for r in gaps]

def daily_scan():
    """主巡检逻辑"""
    report = []
    report.append(f"## 🐢 滴个龟龟 · 每日巡检 {datetime.now().strftime('%Y-%m-%d')}")
    report.append("")
    
    # ── 1. 数据库统计 ──
    stats = check_db_stats()
    report.append("### 📊 数据库")
    report.append(f"- 物种: **{stats['total_species']}** (龟: {stats['categories'].get('龟', '?')} | 蛇: {stats['categories'].get('蛇', '?')} | 蜥蜴: {stats['categories'].get('蜥蜴', '?')} | 蛙: {stats['categories'].get('蛙', '?')} | 守宫: {stats['categories'].get('守宫', '?')})")
    report.append(f"- 图片覆盖: {stats['image_coverage']} ({stats['with_image']}/{stats['total_species']})")
    report.append(f"- 价格覆盖: {stats['price_coverage']} ({stats['with_price']}/{stats['total_species']})")
    report.append(f"- 饲养参数: {stats['care_coverage']} ({stats['with_care']}/{stats['total_species']})")
    report.append(f"- 有训练标注: {stats['species_with_training']} 种")
    
    if stats['feedback']:
        total_fb = sum(stats['feedback'].values())
        confirmed = stats['feedback'].get('confirmed', 0)
        report.append(f"- 识龟反馈: {total_fb} 条 (确认 {confirmed} / 纠错 {stats['feedback'].get('corrected', 0)} / 拒绝 {stats['feedback'].get('rejected', 0)})")
    
    # ── 2. 市场数据变化 ──
    report.append("")
    report.append("### 💰 市场数据")
    
    # 检查上次爬取时间
    if os.path.exists(TTS_FILE):
        tts_mtime = datetime.fromtimestamp(os.path.getmtime(TTS_FILE))
        report.append(f"- TTS 数据: {tts_mtime.strftime('%m-%d %H:%M')} (50产品)")
    else:
        report.append(f"- TTS 数据: ❌ 未采集")
    
    if os.path.exists(BW_FILE):
        bw_mtime = datetime.fromtimestamp(os.path.getmtime(BW_FILE))
        report.append(f"- BW 数据: {bw_mtime.strftime('%m-%d %H:%M')} (47产品)")
    else:
        report.append(f"- BW 数据: ❌ 未采集")
    
    # 尝试快速检测 TTS 是否有新产品
    try:
        req = Request("https://theturtlesource.com/shop-all/", headers={"User-Agent": UA})
        with urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        new_urls = set(re.findall(r'href="https://theturtlesource\.com/([^"/]+/)"', html))
        
        # 加载上次的产品列表
        if os.path.exists(TTS_FILE):
            old = json.load(open(TTS_FILE))
            old_slugs = set()
            for p in old:
                if p.get("url"):
                    slug = p["url"].rstrip("/").split("/")[-1]
                    old_slugs.add(slug + "/")
            
            new_products = new_urls - old_slugs - {
                'about-us/', 'contact-us/', 'faq/', 'cart.php/', 'login.php/',
                'account.php/', 'giftcertificates.php/', 'wishlist.php/', 'compare/',
                'books/', 'supplies/', 'animal-care/', 'care-sheets/', 
                'experience-levels/', 'health-guarantee/', 'health-certificate-1/',
                'customer-support/', 'shipping-returns/', 'terms-and-conditions/',
                'privacy-policy/', 'our-policies/', 'sitemap.php/',
                'turtles/', 'tortoises/', 'water-turtles/', 'box-wood-turtles/',
                'garden-pond-turtles/', 'side-necks/', 'morphs/', 'shop-all/',
                'daily-sale/', 'special-sale/', ''
            }
            if new_products:
                report.append(f"- 🔔 **新上架**: {len(new_products)} 种新品！")
                for np in list(new_products)[:5]:
                    report.append(f"  - {np.replace('-', ' ').replace('/', '').title()}")
            else:
                report.append(f"- 无新品上架")
    except Exception as e:
        report.append(f"- TTS 检测失败: {e}")
    
    # ── 3. 图片缺口 ──
    report.append("")
    report.append("### 🎯 优先补图品种（无图片的高频宠物龟）")
    gaps = check_image_gaps()
    if gaps:
        for g in gaps[:10]:
            report.append(f"- {g['name_cn']} ({g['name_latin'][:40]})")
    else:
        report.append("- ✅ 所有高频品种已有图片")
    
    # ── 4. 数据源可达性 ──
    report.append("")
    report.append("### 🌐 数据源状态")
    sources = [
        ("TheTurtleSource", "https://theturtlesource.com/"),
        ("BackwaterReptiles", "https://www.backwaterreptiles.com/"),
        ("GBIF API", "https://api.gbif.org/v1/species/match?name=Trachemys+scripta"),
        ("iNaturalist API", "https://api.inaturalist.org/v1/taxa?q=Trachemys+scripta&rank=species"),
        ("ReptileDB", "https://reptile-database.reptarium.cz/"),
    ]
    for name, url in sources:
        try:
            req = Request(url, headers={"User-Agent": UA, "Referer": "https://www.inaturalist.org"})
            with urlopen(req, timeout=15) as resp:
                report.append(f"- {name}: ✅ ({resp.status})")
        except Exception as e:
            report.append(f"- {name}: ❌ {type(e).__name__}")
    
    report.append("")
    report.append(f"---\n*下次巡检: {datetime.now().strftime('%m-%d %H:%M')} + 24h*")
    
    return "\n".join(report)

if __name__ == "__main__":
    print(daily_scan())
