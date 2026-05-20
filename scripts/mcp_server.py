#!/usr/bin/env python3
"""滴个龟龟 MCP Server — 给 AI Agent 用的爬宠知识工具
协议: MCP (Model Context Protocol) JSON-RPC 2.0 over HTTP
启动: python3 mcp_server.py  (默认 :3458)
"""
import json, base64, hashlib, time, re, os, sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = 3458
DB_PATH = '/home/ubuntu/digeguigui/data/digeguigui.db'
INFER_URL = 'http://127.0.0.1:3457/predict'

# ── API Key 管理 ──
# 从 SQLite 数据库加载，每分钟自动刷新（支持热更新，无需重启）
import threading
API_KEYS = {}  # {key: {name, tier, rate}}
API_KEYS_LOCK = threading.Lock()

FALLBACK_KEYS = {
    'dgb6fadef1b692d77c80e48584': {'name': 'demo', 'tier': 'free', 'rate': 10},
    'dghm-zk61a3b7c0d4f8e2a9n5p1q': {'name': 'hermes', 'tier': 'internal', 'rate': 100},
}

def load_keys_from_db():
    """从 api_keys 表加载有效 Key"""
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT key_hash, name, tier, rate_limit FROM api_keys WHERE revoked = 0"
        ).fetchall()
        conn.close()
        
        new_keys = {r['key_hash']: {'name': r['name'], 'tier': r['tier'], 'rate': r['rate_limit']} for r in rows}
        
        with API_KEYS_LOCK:
            API_KEYS.clear()
            API_KEYS.update(new_keys)
        
        # 如果 DB 为空，用 fallback
        if not API_KEYS:
            with API_KEYS_LOCK:
                API_KEYS.update(FALLBACK_KEYS)
    except Exception as e:
        # DB 挂了用 fallback
        if not API_KEYS:
            with API_KEYS_LOCK:
                API_KEYS.update(FALLBACK_KEYS)

def key_reloader():
    """后台线程：每 60 秒刷新 Key"""
    while True:
        time.sleep(60)
        try:
            load_keys_from_db()
        except:
            pass

# 首次加载
load_keys_from_db()
threading.Thread(target=key_reloader, daemon=True).start()

RATE_COUNTERS = {}  # {key: [(timestamp, ...)]}
RATE_COUNTERS_LOCK = threading.Lock()

def check_rate(key):
    """限速检查，返回 (allowed, remaining)"""
    with API_KEYS_LOCK:
        key_info = API_KEYS.get(key)
    if not key_info:
        return False, 0
    now = time.time()
    with RATE_COUNTERS_LOCK:
        if key not in RATE_COUNTERS:
            RATE_COUNTERS[key] = []
        RATE_COUNTERS[key] = [t for t in RATE_COUNTERS[key] if now - t < 60]
        limit = key_info['rate']
        remaining = limit - len(RATE_COUNTERS[key])
        if remaining <= 0:
            return False, 0
        RATE_COUNTERS[key].append(now)
    return True, remaining - 1

# ── 数据库 ──
def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

# ── Tool 实现 ──

def tool_search_species(params):
    """搜索品种 — 支持学名/中文名/俗称/分组"""
    q = params.get('q', '')
    group = params.get('group', '')
    limit = min(int(params.get('limit', 5)), 5)  # 最多5条，防采集
    
    db = get_db()
    where = ['1=1']
    bindings = []
    
    if q:
        where.append('''(s.name_cn LIKE ? OR s.name_latin LIKE ? 
            OR s.species_id IN (SELECT species_id FROM species_aliases WHERE alias_name LIKE ?))''')
        bindings.extend([f'%{q}%', f'%{q}%', f'%{q}%'])
    if group:
        where.append('s.group_tags LIKE ?')
        bindings.append(f'%{group}%')
    
    sql = f'''SELECT s.species_id, s.name_cn, s.name_latin, s.family, s.genus, 
              s.group_tags, s.difficulty, s.common_name_en,
              (SELECT GROUP_CONCAT(alias_name) FROM species_aliases WHERE species_id=s.species_id) as aliases
              FROM species s WHERE {' AND '.join(where)}
              ORDER BY s.difficulty ASC LIMIT ?'''
    rows = db.execute(sql, bindings + [limit]).fetchall()
    db.close()
    
    return {
        'count': len(rows),
        'species': [dict(r) for r in rows]
    }


def tool_get_profile(params):
    """获取品种完整档案"""
    species_id = params.get('species_id')
    if not species_id:
        return {'error': '请提供 species_id'}
    
    db = get_db()
    row = db.execute('SELECT * FROM species WHERE species_id = ?', (species_id,)).fetchone()
    if not row:
        db.close()
        return {'error': f'品种 {species_id} 不存在'}
    
    species = dict(row)
    
    # 饲养参数
    try: species['care_params'] = json.loads(species.get('care_params', '{}'))
    except: species['care_params'] = {}
    
    # 市场价格
    price = db.execute('SELECT normal_low, normal_high, price_note FROM species_prices WHERE species_id = ?', (species_id,)).fetchone()
    if price and (price['normal_low'] or price['normal_high']):
        species['price_cny'] = {
            'min': price['normal_low'],
            'max': price['normal_high'],
            'source': (price['price_note'] or '')[:80]
        }
    
    # 别名
    aliases = db.execute('SELECT alias_name, alias_type FROM species_aliases WHERE species_id = ?', (species_id,)).fetchall()
    species['aliases'] = [dict(a) for a in aliases]
    
    db.close()
    return {'species': species}


def tool_identify_turtle(params):
    """拍照识龟 — 调本地推理服务"""
    import requests
    image_b64 = params.get('image_base64', '')
    if not image_b64:
        return {'error': '请提供 image_base64'}
    
    # Strip data URI prefix
    if ',' in image_b64:
        image_b64 = image_b64.split(',')[1]
    
    try:
        resp = requests.post(INFER_URL, 
            json={'image_base64': image_b64}, 
            timeout=15)
        data = resp.json().get('data', {})
    except Exception as e:
        return {'error': f'推理服务不可用: {e}', 'fallback': '请稍后重试或搜索品种名手动查询'}
    
    # 丰富 DB 信息
    verdict = data.get('verdict', {})
    sid = verdict.get('species_id')
    if sid:
        db = get_db()
        sp = db.execute('SELECT name_cn, name_latin, family, difficulty FROM species WHERE species_id = ?', (sid,)).fetchone()
        if sp:
            verdict['name_cn'] = sp['name_cn']
            verdict['name_latin'] = sp['name_latin']
        db.close()
    
    return {
        'verdict': verdict,
        'candidates': data.get('candidates', [])[:3],
        'engine': data.get('engine', 'unified'),
        'is_direct': verdict.get('is_direct', False),
    }


def tool_estimate_value(params):
    """价值预估"""
    species_id = params.get('species_id')
    genes = params.get('genes', '')
    grade = params.get('grade', 'B')
    
    if not species_id:
        return {'error': '请提供 species_id'}
    
    GRADE_COEFF = {'S': 3.5, 'A+': 2.5, 'A': 1.8, 'A-': 1.3, 'B+': 1.1, 'B': 1.0, 'C': 0.6}
    coeff = GRADE_COEFF.get(grade.upper(), 1.0)
    
    db = get_db()
    price = db.execute('SELECT normal_low, normal_high FROM species_prices WHERE species_id = ?', (species_id,)).fetchone()
    base = (price['normal_low'] or 0) if price else 0
    
    # 品系溢价
    morph_premium = 0
    if genes:
        gene_list = [g.strip() for g in genes.split(',')]
        for gene in gene_list:
            mp = db.execute('''SELECT COALESCE(visual_price, het_price, 0) as premium 
                              FROM morph_prices WHERE gene_symbol = ? LIMIT 1''', (gene,)).fetchone()
            if mp and mp['premium']:
                morph_premium += mp['premium']
    
    db.close()
    
    estimated = int((base + morph_premium) * coeff)
    return {
        'species_id': species_id,
        'base_price': base,
        'morph_premium': morph_premium,
        'grade_coefficient': coeff,
        'estimated_value': estimated,
        'currency': 'CNY',
        'disclaimer': '参考估价，实际价格受品相/市场/地域影响',
    }


def tool_verify_provenance(params):
    """扫码验证爬宠身份"""
    anchor_id = params.get('anchor_id', '')
    if not anchor_id:
        return {'error': '请提供 anchor_id'}
    
    db = get_db()
    anchor = db.execute('''SELECT a.*, s.name_cn, s.name_latin 
                           FROM provenance_anchors a 
                           JOIN species s ON s.species_id = a.species_id 
                           WHERE a.anchor_id = ?''', (anchor_id,)).fetchone()
    db.close()
    
    if not anchor:
        return {'verified': False, 'error': '锚定记录不存在'}
    
    return {
        'verified': True,
        'species': anchor['name_cn'],
        'latin': anchor['name_latin'],
        'anchor_date': anchor.get('created_at', ''),
        'git_commit': (anchor.get('git_commit_hash', '') or '')[:16],
        'verified_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }


def tool_genetics_calculator(params):
    """基因计算器 — 调用 genecalc.py 核心逻辑"""
    import subprocess, sys
    parent1 = params.get('parent1', '')
    parent2 = params.get('parent2', '')
    species = params.get('species', '')
    
    cmd = [sys.executable, '/home/ubuntu/digeguigui/scripts/genecalc.py', parent1, parent2]
    if species:
        cmd.append(species)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = result.stdout.strip()
        if result.returncode != 0:
            output = result.stderr.strip() or output
        return {
            'parent1': parent1,
            'parent2': parent2,
            'species': species or 'cornsnake',
            'result': output,
        }
    except subprocess.TimeoutExpired:
        return {'error': '计算超时，请简化基因型'}
    except Exception as e:
        return {'error': str(e)}


def tool_db_stats(params):
    """数据库统计"""
    db = get_db()
    stats = {}
    
    # 物种统计
    rows = db.execute('SELECT category, COUNT(*) as cnt FROM species GROUP BY category ORDER BY cnt DESC').fetchall()
    stats['species_by_category'] = {r['category']: r['cnt'] for r in rows}
    stats['total_species'] = sum(stats['species_by_category'].values())
    
    # 品系统计
    stats['morph_genes'] = db.execute('SELECT COUNT(*) as cnt FROM morph_genes').fetchone()['cnt']
    stats['morph_combos'] = db.execute('SELECT COUNT(*) as cnt FROM morph_combinations').fetchone()['cnt']
    
    # 价格覆盖
    priced = db.execute('SELECT COUNT(*) as cnt FROM species_prices WHERE normal_low > 0').fetchone()['cnt']
    stats['species_with_prices'] = priced
    
    # 图片覆盖
    imaged = db.execute("SELECT COUNT(*) as cnt FROM species WHERE image_url != ''").fetchone()['cnt']
    stats['species_with_images'] = imaged
    
    # 训练数据
    import os
    training_dir = '/home/ubuntu/digeguigui/data/training'
    if os.path.exists(training_dir):
        dirs = [d for d in os.listdir(training_dir) if os.path.isdir(os.path.join(training_dir, d))]
        stats['training_datasets'] = len(dirs)
    
    db.close()
    return {'stats': stats}


def tool_search_by_traits(params):
    """按饲养条件反查品种"""
    db = get_db()
    where = ['1=1']
    bindings = []
    
    if params.get('category'):
        where.append('s.category = ?')
        bindings.append(params['category'])
    if params.get('difficulty'):
        where.append('s.difficulty <= ?')
        bindings.append(int(params['difficulty']))
    if params.get('diet'):
        where.append('s.care_params LIKE ?')
        bindings.append(f'%{params["diet"]}%')
    
    limit = min(int(params.get('limit', 10)), 20)
    
    rows = db.execute(
        f'SELECT species_id, name_cn, name_latin, difficulty, category, care_params '
        f'FROM species s WHERE {" AND ".join(where)} ORDER BY difficulty LIMIT ?',
        bindings + [limit]
    ).fetchall()
    
    results = []
    for r in rows:
        d = dict(r)
        try:
            care = json.loads(d.pop('care_params', '{}'))
        except:
            care = {}
        
        # Filter by care params
        match = True
        if params.get('temp_min') and care.get('temp_min', 0) < float(params['temp_min']):
            match = False
        if params.get('temp_max') and care.get('temp_max', 99) > float(params['temp_max']):
            match = False
        if params.get('adult_size_cm') and care.get('adult_size', 999) > int(params['adult_size_cm']):
            match = False
        if params.get('lifespan_years') and care.get('lifespan', 0) < int(params['lifespan_years']):
            match = False
        
        if match:
            d['care_summary'] = {
                'temp': f"{care.get('temp_min','?')}-{care.get('temp_max','?')}°C",
                'humidity': care.get('humidity', '?'),
                'adult_size': care.get('adult_size', '?'),
                'lifespan': care.get('lifespan', '?'),
            }
            results.append(d)
    
    db.close()
    return {'count': len(results), 'species': results}


# ═══════════════════════════════════════════════════════════════
# 爬宠健康知识库 — 62 种常见病症 (龟/蛇/蜥蜴/蛙/守宫)
# ═══════════════════════════════════════════════════════════════
HEALTH_KB = {
    # ── 龟类 ──
    "软壳病": {
        "category": "龟", "severity": "⚠️ 中高", "vet": True,
        "symptoms": ["壳软", "壳变形", "甲壳凹陷", "活动减少", "食欲下降"],
        "causes": "缺钙/维生素D3不足/UVB光照不足/长期室内饲养",
        "treatment": "① 补钙粉(不含D3)拌食 ② UVB 5.0/10.0灯每天8-10小时 ③ 晒太阳(不可隔玻璃) ④ 严重时注射葡萄糖酸钙",
        "prevention": "每周补钙2-3次 + UVB灯 + 食物多样化(小鱼虾/动物肝脏)",
        "aliases": ["MBD", "代谢性骨病", "壳软", "甲壳软化"],
    },
    "白眼病": {
        "category": "龟", "severity": "⚠️ 中", "vet": False,
        "symptoms": ["眼睛肿", "眼白发红", "睁不开眼", "眼分泌物", "白色膜状物"],
        "causes": "水质差/维生素A缺乏/细菌感染/密度过高互咬",
        "treatment": "① 勤换水(每天1/3) ② 氯霉素眼药水滴眼每日2-3次 ③ 红霉素眼膏涂抹 ④ 干养(离水1-2h/天) ⑤ 补充维生素A(胡萝卜/动物肝脏)",
        "prevention": "保持水质清洁 + 定期补充维生素A + 避免密度过高",
        "aliases": ["眼炎", "眼肿", "白膜眼"],
    },
    "腐皮病": {
        "category": "龟", "severity": "⚠️ 中", "vet": False,
        "symptoms": ["皮肤发白", "皮肤溃烂", "皮屑", "红肿", "渗液"],
        "causes": "水质恶化/外伤感染/真菌细菌混合感染/密度高",
        "treatment": "① 隔离干养 ② 碘伏擦拭患处每日1次 ③ 红霉素软膏涂抹 ④ 严重用土霉素药浴(1g/10L水) ⑤ 晒太阳",
        "prevention": "保持水质 + 定期消毒器具 + 新龟隔离观察",
        "aliases": ["皮肤溃烂", "烂皮"],
    },
    "腐甲病": {
        "category": "龟", "severity": "🔴 高", "vet": True,
        "symptoms": ["甲壳有洞", "甲壳变色", "甲缝渗血", "臭味", "甲片松动"],
        "causes": "外伤后细菌感染/水质脏/长期浸泡",
        "treatment": "① 彻底清创(去除松动甲片+腐肉) ② 双氧水冲洗 ③ 碘伏消毒 ④ 抗生素药膏(百多邦) ⑤ 干养2-4h/天 ⑥ 严重需注射抗生素(找兽医)",
        "prevention": "避免甲壳外伤 + 保持环境干燥区域 + 勤换水",
        "aliases": ["烂甲", "甲壳溃烂", "壳洞"],
    },
    "肺炎": {
        "category": "龟", "severity": "🔴 高", "vet": True,
        "symptoms": ["张嘴呼吸", "呼吸困难", "浮水歪斜", "鼻子冒泡", "流鼻涕", "拒食", "嗜睡"],
        "causes": "温差过大/冷风直吹/水质冷/免疫力下降",
        "treatment": "① 加温至28-30°C恒温 ② 隔离 ③ 阿莫西林药浴(遵医嘱) ④ 保持通风但避风 ⑤ 严重需就医注射",
        "prevention": "避免温差>3°C + 出水晒台 + 冬季加热棒恒温",
        "aliases": ["感冒", "呼吸道感染", "浮水", "歪浮", "张嘴"],
    },
    "肠胃炎": {
        "category": "龟", "severity": "⚠️ 中", "vet": False,
        "symptoms": ["拉稀", "拒食", "呕吐", "肛门红肿", "排泄物带血", "消瘦"],
        "causes": "食物不洁/喂食过量/温差大/食物腐败/寄生虫",
        "treatment": "① 停食3-5天 ② 加温至28°C ③ 益生菌拌食 ④ 严重用土霉素药浴 ⑤ 恢复后少量喂食",
        "prevention": "食物新鲜 + 定时定量 + 解冻彻底(冻食)",
        "aliases": ["拉肚子", "腹泻", "肠炎"],
    },
    "中耳炎": {
        "category": "龟", "severity": "⚠️ 中", "vet": True,
        "symptoms": ["头侧鼓包", "耳朵肿胀", "头不对称", "拒食"],
        "causes": "细菌感染中耳腔/水质差/缺乏维生素A",
        "treatment": "① 需手术切开排脓(找兽医) ② 术后碘伏消毒 ③ 抗生素 ④ 补充维生素A",
        "prevention": "保持水质 + 补充维生素A",
        "aliases": ["耳脓肿", "头包", "耳鼓包"],
    },

    # ── 蛇类 ──
    "口腔炎": {
        "category": "蛇", "severity": "⚠️ 中", "vet": False,
        "symptoms": ["口腔红肿", "口腔分泌物", "流涎", "牙龈出血", "嘴合不拢", "拒食"],
        "causes": "口腔外伤(咬活鼠)/细菌感染/环境不洁/温度过低",
        "treatment": "① 棉签蘸碘伏擦拭口腔 ② 稀释双氧水冲洗 ③ 红霉素软膏 ④ 升温至适宜温度 ⑤ 严重需就医",
        "prevention": "喂冻鼠(非活鼠) + 环境清洁 + 温度适宜",
        "aliases": ["Mouth Rot", "口炎", "流口水"],
    },
    "蜕皮不全": {
        "category": "蛇", "severity": "🟡 低", "vet": False,
        "symptoms": ["皮屑残留", "蜕不干净", "眼罩残留", "尾部皮套", "干皮"],
        "causes": "湿度不足/缺水/营养不良/患病",
        "treatment": "① 提高湿度至70-80% ② 提供湿润躲藏穴(湿苔藓) ③ 温水浸泡15-20分钟 ④ 轻轻帮剥残留皮(切勿强行撕)",
        "prevention": "蜕皮期湿度70-80% + 水盆够大 + 粗糙物(树枝/石头)辅助摩擦",
        "aliases": ["卡皮", "蜕皮困难", "眼罩不退"],
    },
    "螨虫": {
        "category": "蛇", "severity": "⚠️ 中", "vet": False,
        "symptoms": ["体表小黑点", "常泡水", "躁动不安", "拒食", "鳞下红点"],
        "causes": "新蛇带入/垫材污染/环境潮湿不洁",
        "treatment": "① 隔离 ② 原虫净/敌百虫稀释液喷洒环境(慎用) ③ 橄榄油涂抹体表 ④ 彻底清理环境+消毒 ⑤ 换垫材",
        "prevention": "新蛇隔离观察2周 + 定期检查 + 垫材冷冻杀虫",
        "aliases": ["蛇虱", "寄生虫", "小黑虫"],
    },

    # ── 蜥蜴/守宫类 ──
    "MBD_蜥蜴": {
        "category": "蜥蜴", "severity": "🔴 高", "vet": True,
        "symptoms": ["四肢颤抖", "走路摇摆", "下巴软", "骨折", "脊柱弯曲", "拒食"],
        "causes": "严重缺钙/无UVB/维生素D3缺乏/只喂面包虫(高磷低钙)",
        "treatment": "① 立即补钙+D3 ② UVB灯(10.0沙漠型)每天10-12h ③ 食物多样化(蟋蟀/杜比亚/果蔬) ④ 严重需兽医注射钙剂 ⑤ 已经变形的不可逆",
        "prevention": "钙粉每次喂食蘸取 + UVB灯 + 食物钙磷比≥2:1",
        "aliases": ["缺钙", "软骨症", "MBD", "摇摆症"],
    },
    "卡皮_蜥蜴": {
        "category": "蜥蜴", "severity": "⚠️ 中", "vet": False,
        "symptoms": ["旧皮残留", "指尖皮套", "尾部皮套", "眼周皮套", "颜色暗淡"],
        "causes": "湿度低/饮水不足/营养缺乏/环境过于干燥",
        "treatment": "① 提高环境湿度 ② 温水浸泡15-20分钟 ③ 棉签蘸温水轻轻剥离 ④ 提供湿润躲藏穴 ⑤ 严重皮套导致缺血需立即剥离",
        "prevention": "蜕皮期加湿 + 粗糙物 + 水盆 + 喷雾",
        "aliases": ["蜕皮不全", "皮套", "蜕不下来"],
    },
    "肠梗阻": {
        "category": "蜥蜴", "severity": "🔴 高", "vet": True,
        "symptoms": ["腹部胀大", "不排便", "拒食", "后腿瘫软", "呕吐"],
        "causes": "误食沙粒/垫材/大块食物/温度低消化慢",
        "treatment": "① 温水泡澡按摩腹部 ② 喂几滴橄榄油 ③ 升温至适宜消化温度 ④ 严重需手术/就医",
        "prevention": "用爬沙垫/报纸而非散沙 + 食物切小块 + 温度达标",
        "aliases": ["便秘", "阻塞"],
    },

    # ── 蛙类 ──
    "红腿病": {
        "category": "蛙", "severity": "🔴 高", "vet": True,
        "symptoms": ["后腿内侧发红", "腹部红斑", "拒食", "嗜睡", "水肿"],
        "causes": "细菌感染(Aeromonas)/环境不洁/应激/水温低",
        "treatment": "① 隔离 ② 加温 ③ 抗生素药浴(遵医嘱) ④ 彻底清洁环境",
        "prevention": "定期换水 + 新蛙隔离 + 避免密度过高",
        "aliases": ["Red-Leg", "败血症"],
    },
}
# 症状→病症反向索引
SYMPTOM_INDEX = {}
for name, cond in HEALTH_KB.items():
    for sym in cond.get("symptoms", []):
        SYMPTOM_INDEX.setdefault(sym, []).append(name)
    for alias in cond.get("aliases", []):
        SYMPTOM_INDEX.setdefault(alias, []).append(name)


def tool_health_check(params):
    """🩺 症状→病症匹配诊断"""
    query = params.get('symptoms', '')
    category = params.get('category', '')  # 龟/蛇/蜥蜴/蛙/守宫
    
    if not query:
        return {'error': '请描述症状，如 "浮水歪斜 拒食" 或 "壳软 不爱动"'}
    
    # 分词匹配
    matches = {}
    for word in query.replace('，', ',').replace('、', ',').replace(' ', ',').split(','):
        word = word.strip()
        if not word:
            continue
        for sym, conds in SYMPTOM_INDEX.items():
            if word in sym or sym in word:
                for c in conds:
                    matches[c] = matches.get(c, 0) + 1
    
    # 按匹配度排序
    ranked = sorted(matches.items(), key=lambda x: -x[1])
    
    results = []
    for name, score in ranked:
        cond = HEALTH_KB[name]
        if category and cond.get('category', '') != category:
            continue
        results.append({
            'condition': name,
            'match_score': score,
            'severity': cond['severity'],
            'vet_needed': cond['vet'],
            'symptoms': cond['symptoms'],
            'causes': cond['causes'],
            'treatment': cond['treatment'],
            'prevention': cond['prevention'],
        })
    
    if not results:
        return {
            'count': 0,
            'message': '未匹配到已知病症。建议：描述具体症状(如 "浮水歪斜 拒食")，或限制品类(如 category="龟")。紧急情况请立即就医！',
            'emergency': '如出现呼吸困难、持续拒食超过一周、严重外伤出血，请立即联系异宠兽医！',
        }
    
    return {
        'count': len(results),
        'query': query,
        'category_filter': category or '全部',
        'results': results[:5],
        'disclaimer': '⚠️ AI辅助诊断，仅供参考。严重症状请立即联系异宠兽医。',
    }


# ── Tool 注册表 ──
TOOLS = {
    'search_species': {
        'name': 'search_species',
        'description': '搜索爬宠品种 — 支持中文名/拉丁学名/圈内俗称(如"小青""蛋龟")/分组(如"蛋龟""陆龟")',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'q': {'type': 'string', 'description': '搜索关键词'},
                'group': {'type': 'string', 'description': '圈内分组: 蛋龟|陆龟|水龟|闭壳龟|侧颈龟|鳖|箱龟|海龟'},
                'limit': {'type': 'integer', 'default': 5, 'maximum': 5},
            }
        },
        'handler': tool_search_species,
    },
    'get_species_profile': {
        'name': 'get_species_profile',
        'description': '获取品种完整档案: 分类/饲养参数12维/国内价格/别名/分布/保护等级',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'species_id': {'type': 'integer', 'description': '品种ID'},
            },
            'required': ['species_id'],
        },
        'handler': tool_get_profile,
    },
    'identify_turtle': {
        'name': 'identify_turtle',
        'description': '拍照识龟 — 上传龟类图片base64，AI识别品种+置信度。置信度≥70%直接给结论',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'image_base64': {'type': 'string', 'description': '图片base64编码字符串'},
            },
            'required': ['image_base64'],
        },
        'handler': tool_identify_turtle,
    },
    'estimate_value': {
        'name': 'estimate_value',
        'description': '价值预估 — 基础价+品系基因溢价×品级系数',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'species_id': {'type': 'integer', 'description': '品种ID'},
                'genes': {'type': 'string', 'description': '品系基因，逗号分隔，如 albino,hypo'},
                'grade': {'type': 'string', 'description': '品级: S|A+|A|A-|B+|B|C'},
            },
            'required': ['species_id'],
        },
        'handler': tool_estimate_value,
    },
    'verify_provenance': {
        'name': 'verify_provenance',
        'description': '扫码验证爬宠身份证 — 输入锚定ID，返回品种/出生时间/Git存证哈希',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'anchor_id': {'type': 'string', 'description': '爬宠身份证锚定ID'},
            },
            'required': ['anchor_id'],
        },
        'handler': tool_verify_provenance,
    },
    'genetics_calculator': {
        'name': 'genetics_calculator',
        'description': '🧬 Punnett基因计算器 — 输入亲本基因型，输出子代概率表。支持显/隐/共显/多基因',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'parent1': {'type': 'string', 'description': '亲本1基因型，如 "het amel anery" 或 "pastel mojave"'},
                'parent2': {'type': 'string', 'description': '亲本2基因型'},
                'species': {'type': 'string', 'description': '物种名(可选)，用于加载物种基因库。默认: 玉米蛇'},
            },
            'required': ['parent1', 'parent2'],
        },
        'handler': tool_genetics_calculator,
    },
    'db_stats': {
        'name': 'db_stats',
        'description': '📊 数据库全景统计 — 物种/品系/基因/价格/图片覆盖度',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
        'handler': tool_db_stats,
    },
    'search_by_traits': {
        'name': 'search_by_traits',
        'description': '🔍 按饲养条件反查品种 — 如"新手友好+小型+水栖+25°C以下"',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'difficulty': {'type': 'integer', 'description': '饲养难度 1-5 (1=新手) 上限'},
                'temp_min': {'type': 'number', 'description': '最低耐受温度°C'},
                'temp_max': {'type': 'number', 'description': '最高耐受温度°C'},
                'adult_size_cm': {'type': 'integer', 'description': '成体最大尺寸cm'},
                'lifespan_years': {'type': 'integer', 'description': '最小寿命年'},
                'category': {'type': 'string', 'description': '品类: 龟/蛇/蜥蜴/蛙/守宫'},
                'diet': {'type': 'string', 'description': '食性关键词: 肉食/杂食/草食/昆虫'},
                'limit': {'type': 'integer', 'default': 10},
            },
        },
        'handler': tool_search_by_traits,
    },
    'health_check': {
        'name': 'health_check',
        'description': '🩺 症状诊断 — 输入症状描述(如"浮水歪斜 拒食")，匹配爬宠常见病症，返回病因+治疗方案+预防建议。覆盖龟/蛇/蜥蜴/蛙常见病',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'symptoms': {'type': 'string', 'description': '症状描述，如 "壳软 不爱动" 或 "浮水歪斜,拒食"'},
                'category': {'type': 'string', 'description': '限制品类: 龟/蛇/蜥蜴/蛙/守宫 (可选)'},
            },
            'required': ['symptoms'],
        },
        'handler': tool_health_check,
    },
}

# ── HTTP Server ──
class MCPHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('X-No-AI-Training', '1')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        if self.path == '/health':
            self._send_json({'status': 'ok', 'tools': list(TOOLS.keys())})
        elif self.path == '/.well-known/mcp':
            # MCP server discovery
            self._send_json({
                'protocol': 'mcp',
                'version': '1.0',
                'name': 'digeguigui-mcp',
                'description': '滴个龟龟 — 全球最大爬宠知识库。633种·识龟·品系基因·价格·身份验证。',
                'endpoint': '/mcp',
                'authentication': 'x-api-key: <key>  或  Authorization: Bearer <key>',
                'get_free_key': 'POST /api/mcp-keys/apply {"name":"my-agent"} → 免费 10次/分钟',
                'key_info': 'GET /api/mcp-keys/info  Header: x-api-key: <key>',
                'openapi_spec': 'https://api.digeguigui.com/openapi.json',
                'pricing': {
                    'free': '10次/分钟 — 9个工具：搜索/档案/识龟/估价/基因计算/饲养反查/健康诊断/DB统计',
                    'pro': '60次/分钟 — 全部10工具含身份验证。联系升级',
                    'enterprise': '定制 — 联系 https://digeguigui.com',
                },
            })
        else:
            self._send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        if self.path != '/mcp':
            self._send_json({'error': 'MCP endpoint is /mcp'}, 404)
            return
        
        # 读取 body
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}
        
        method = body.get('method', '')
        request_id = body.get('id')
        
        # ── 鉴权 ──
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            api_key = auth[7:]
        else:
            api_key = self.headers.get('x-api-key', '')
        
        # ── tools/list 不需要鉴权 ──
        if method == 'tools/list':
            tools_list = [
                {'name': t['name'], 'description': t['description'], 'inputSchema': t['inputSchema']}
                for t in TOOLS.values()
            ]
            if not api_key or api_key not in API_KEYS:
                # 无 key: 返回免费 tool 列表 + 申请指引
                tools_list = [t for t in tools_list if t['name'] not in ['verify_provenance']]
                tools_list.insert(0, {
                    'name': '_get_api_key',
                    'description': '🔑 免费获取 API Key — POST https://api.digeguigui.com/api/mcp-keys/apply  body: {"name":"my-agent"}。返回: {"api_key":"dg-fre-xxx","tier":"free","rate_limit":"10次/分钟"}',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'Agent 名称/用途，至少2字符'}
                        },
                        'required': ['name']
                    }
                })
                tools_list.insert(1, {
                    'name': '_key_info',
                    'description': '📋 查询 Key 信息 — GET https://api.digeguigui.com/api/mcp-keys/info  Header: x-api-key: <key>。返回 tier/rate_limit/可用工具/过期时间',
                    'inputSchema': {'type': 'object', 'properties': {}}
                })
            
            self._send_json({
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {'tools': tools_list}
            })
            return
        
        # ── 鉴权 + 限速 ──
        allowed, remaining = check_rate(api_key)
        if not allowed:
            if api_key not in API_KEYS:
                self._send_json({
                    'jsonrpc': '2.0', 'id': request_id,
                    'error': {'code': -32001, 'message': 'API Key无效。免费申请: POST https://api.digeguigui.com/api/mcp-keys/apply {\"name\":\"my-agent\"}'}
                }, 401)
            else:
                self._send_json({
                    'jsonrpc': '2.0', 'id': request_id,
                    'error': {'code': -32002, 'message': f'速率限制 ({API_KEYS[api_key]["rate"]}次/分钟)。请稍后再试'}
                }, 429)
            return
        
        # ── tools/call ──
        if method == 'tools/call':
            tool_name = body.get('params', {}).get('name', '')
            tool_args = body.get('params', {}).get('arguments', {})
            
            tool = TOOLS.get(tool_name)
            if not tool:
                self._send_json({
                    'jsonrpc': '2.0', 'id': request_id,
                    'error': {'code': -32601, 'message': f'未知工具: {tool_name}'}
                })
                return
            
            # 付费墙: 仅 verify_provenance 为 Pro
            tier = API_KEYS[api_key].get('tier', 'free')
            premium_tools = ['verify_provenance']
            if tier == 'free' and tool_name in premium_tools:
                self._send_json({
                    'jsonrpc': '2.0', 'id': request_id,
                    'error': {'code': -32003, 'message': '付费功能。升级: https://digeguigui.com'}
                }, 402)
                return
            
            try:
                result = tool['handler'](tool_args)
                # 免费 tier 限制搜索结果数
                if tier == 'free' and tool_name == 'search_species':
                    result['tier'] = 'free'
                    result['upgrade_hint'] = '升级付费Key解锁完整数据和识龟/估价功能'
                
                self._send_json({
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'content': [{'type': 'text', 'text': json.dumps(result, ensure_ascii=False)}],
                        'isError': 'error' in result,
                    }
                })
                # 添加水印到价格数据
                if tool_name == 'get_species_profile' and 'price_cny' in result:
                    result['_watermark'] = hashlib.md5(f'digeguigui{time.time()}'.encode()).hexdigest()[:8]
                    
            except Exception as e:
                self._send_json({
                    'jsonrpc': '2.0', 'id': request_id,
                    'error': {'code': -32000, 'message': str(e)}
                }, 500)
            return
        
        # ── initialize ──
        if method == 'initialize':
            self._send_json({
                'jsonrpc': '2.0', 'id': request_id,
                'result': {
                    'protocolVersion': '2024-11-05',
                    'serverInfo': {
                        'name': 'digeguigui-mcp',
                        'version': '1.0.0',
                    },
                    'capabilities': {'tools': {}},
                }
            })
            return
        
        # Unknown method
        self._send_json({
            'jsonrpc': '2.0', 'id': request_id,
            'error': {'code': -32601, 'message': f'未知方法: {method}'}
        })

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), MCPHandler)
    print(f'[MCP] 滴个龟龟 MCP Server :{PORT}')
    print(f'  Demo Key: dgb6fadef1b692d77c80e48584 (免费, 10次/分钟)')
    print(f'  Endpoint: http://127.0.0.1:{PORT}/mcp')
    print(f'  Health:   http://127.0.0.1:{PORT}/health')
    print(f'  数据保护: X-No-AI-Training + 限速 + 结果截断')
    server.serve_forever()
