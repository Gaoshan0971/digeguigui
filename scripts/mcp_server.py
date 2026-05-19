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
# 格式: {key: {name, tier, rate_limit_per_min}}
API_KEYS = {
    'dgb6fadef1b692d77c80e48584': {'name': 'demo', 'tier': 'free', 'rate': 10},  # 免费: 10次/分钟
}
RATE_COUNTERS = {}  # {key: [(timestamp, ...)]}

def check_rate(key):
    """限速检查，返回 (allowed, remaining)"""
    if key not in API_KEYS:
        return False, 0
    now = time.time()
    if key not in RATE_COUNTERS:
        RATE_COUNTERS[key] = []
    # Clean old entries
    RATE_COUNTERS[key] = [t for t in RATE_COUNTERS[key] if now - t < 60]
    limit = API_KEYS[key]['rate']
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
                'description': '滴个龟龟 — 爬宠异宠知识工具。识龟/品种档案/价格/身份验证。',
                'endpoint': '/mcp',
                'authentication': 'Bearer API-Key header',
                'pricing': '免费Key限速10次/分钟',
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
                # 无 key: 返回免费 tool 列表
                tools_list = [t for t in tools_list if t['name'] in ['search_species', 'get_species_profile']]
                tools_list.insert(0, {
                    'name': '_get_api_key',
                    'description': '⚠️ 需要API Key才能使用完整功能。免费Key: 搜索+档案。付费Key: 识龟+估价+验证。申请: https://digeguigui.com',
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
                    'error': {'code': -32001, 'message': 'API Key无效。申请: https://digeguigui.com'}
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
            
            # 付费墙: 免费 tier 限制
            tier = API_KEYS[api_key].get('tier', 'free')
            premium_tools = ['identify_turtle', 'estimate_value', 'verify_provenance']
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
