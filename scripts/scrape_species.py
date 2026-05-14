#!/usr/bin/env python3
"""
scrape_species.py — 爬取百度百科龟类品系数据，输出 JSON
用法: /usr/bin/python3 scripts/scrape_species.py
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import sys
import os
import re

# ========== 配置 ==========
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'species_mvp.json')
REQUEST_DELAY = 3
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

SPECIES_LIST = [
    "剃刀龟",
    "麝香龟",
    "巨头麝香龟",
    "平背麝香龟",
    "白唇泥龟",
    "红面泥龟",
    "黄泽泥龟",
    "果核泥龟",
    "牟氏水龟",
    "鹰嘴泥龟",
]


def fetch_page(name_cn):
    url = f"https://baike.baidu.com/item/{name_cn}"
    try:
        resp = requests.get(url, headers={'User-Agent': UA}, timeout=15)
        resp.encoding = 'utf-8'
        if resp.status_code == 200 and '抱歉，您所访问的页面不存在' not in resp.text:
            return resp.text
    except Exception as e:
        print(f"  ⚠️ 请求失败: {e}", file=sys.stderr)
    return None


def parse_baike(html):
    soup = BeautifulSoup(html, 'lxml')
    data = {}

    # ===== 标题 =====
    h1 = soup.select_one('h1')
    data['baike_title'] = h1.text.strip() if h1 else ''

    # ===== Infobox: dt/dd 对 =====
    basic = soup.select_one('[class*=basicInfo]')
    if basic:
        for dt, dd in zip(basic.select('dt'), basic.select('dd')):
            key = dt.text.strip().replace('\xa0', '')
            val = dd.text.strip().replace('\xa0', '')
            data[key] = val

    # ===== 摘要 =====
    summary = soup.select_one('[class*=lemmaSummary], [class*=summary_BWeRr], .lemma-summary')
    if summary:
        data['summary'] = summary.text.strip()

    return data


def parse_size_lifespan(text):
    """从摘要文本中提取体型和寿命"""
    size = None
    lifespan = None

    # 体型模式：背甲长XX厘米、体长XXcm、可达XXcm
    size_patterns = [
        r'背甲(?:长|长度)?\s*(?:约|可达|为)?\s*(\d+[\.\d]*)\s*(?:[-~至]\s*(\d+[\.\d]*))?\s*(?:厘米|cm)',
        r'体长\s*(?:约|可达|为)?\s*(\d+[\.\d]*)\s*(?:[-~至]\s*(\d+[\.\d]*))?\s*(?:厘米|cm)',
        r'(?:可达|最大|最长)\s*(\d+[\.\d]*)\s*(?:厘米|cm)',
        r'(\d+[\.\d]*)\s*(?:[-~至]\s*(\d+[\.\d]*))?\s*(?:厘米|cm)\s*(?:左右|的)?.{0,10}(?:背甲|体长|体型)',
    ]
    for pat in size_patterns:
        m = re.search(pat, text)
        if m:
            if m.group(2):
                size = float(m.group(2))  # 取上限
            else:
                size = float(m.group(1))
            break

    # 寿命模式
    lifespan_patterns = [
        r'寿命\s*(?:约|可达|为)?\s*(\d+)\s*(?:[-~至]\s*(\d+))?\s*年',
        r'(?:可达|最长|能活|可活)\s*(\d+)\s*年',
        r'(\d+)\s*(?:[-~至]\s*(\d+))?\s*年\s*(?:的|左右)?.{0,10}(?:寿命|生命)',
    ]
    for pat in lifespan_patterns:
        m = re.search(pat, text)
        if m:
            lifespan = int(m.group(2) if m.group(2) else m.group(1))
            break

    return size, lifespan


def parse_temperature(text):
    """从文本中提取温度范围"""
    patterns = [
        r'(\d+)\s*[-~至]\s*(\d+)\s*℃',
        r'(\d+)\s*[-~]\s*(\d+)\s*°C',
        r'温度\s*(?:约|为)?\s*(\d+)\s*[-~至]\s*(\d+)',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return f"{m.group(1)}-{m.group(2)}°C"
    return None


def parse_distribution(text):
    """从文本中提取分布"""
    patterns = [
        r'原产(?:于|地)?(.{2,30}?)(?:[。，,;；\s]|$)',
        r'分布(?:于|在)?(.{2,30}?)(?:[。，,;；\s]|$)',
        r'产于(.{2,30}?)(?:[。，,;；\s]|$)',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip().rstrip('，。')
    return None


def extract_traits(text):
    """从摘要提取关键特征"""
    traits = []
    trait_map = {
        '龙骨背甲': ['龙骨', '棱脊', '脊棱', '棘突', '屋顶状', '刀背', '屋脊'],
        '夜行性': ['夜行', '夜间'],
        '底栖': ['底栖', '水底', '底层'],
        '体型小巧': ['小巧', '小型', '迷你'],
        '性格温顺': ['温顺', '温和', '胆小', '羞怯'],
        '活泼好动': ['活泼', '好动'],
        '肉食性': ['肉食', '肉食性'],
        '杂食性': ['杂食', '杂食性'],
    }
    for trait, keywords in trait_map.items():
        for kw in keywords:
            if kw in text:
                traits.append(trait)
                break
    return traits


def extract_fields(raw, name_cn):
    """从百度百科解析结果中提取目标字段"""
    summary = raw.get('summary', '')
    full_text = summary

    # 基础字段映射
    FIELD_MAP = {
        '中文学名': 'baike_name_cn',
        '拉丁学名': 'name_latin',
        '外文名': 'common_name_en',
        '英文名': 'common_name_en',
        '科': 'family',
        '属': 'genus',
        '保护级别': 'conservation',
    }

    mapped = {}
    for bk_key, bk_val in raw.items():
        target = FIELD_MAP.get(bk_key)
        if target:
            mapped[target] = bk_val

    # 分布
    raw_dist = raw.get('分布区域', '') or raw.get('地理分布', '')
    if not raw_dist:
        raw_dist = parse_distribution(summary)
    mapped['distribution'] = raw_dist or parse_distribution(summary)

    # 体型和寿命
    size, lifespan = parse_size_lifespan(summary)
    mapped['size_max_cm'] = size
    mapped['lifespan_years'] = lifespan

    # 温度
    temp = parse_temperature(summary)
    mapped['temp_range'] = temp

    # CITES
    cites_raw = raw.get('CITES', '')
    mapped['cites'] = cites_raw if cites_raw else None

    # 关键特征
    key_traits = extract_traits(summary)
    if '龙骨背甲' in str(raw.get('别名', '')):
        key_traits.append('龙骨背甲')

    # 饲养难度估算
    diff = 2  # 蛋龟默认
    conservation = mapped.get('conservation', '')
    if '濒危' in str(conservation) or '易危' in str(conservation) or 'EN' in str(conservation):
        diff = 4
    elif '近危' in str(conservation) or 'VU' in str(conservation):
        diff = 3
    elif size and float(size) > 20:
        diff = 3
    mapped['difficulty'] = diff

    # ===== 组装最终结果 =====
    result = {
        "name_cn": name_cn,
        "name_latin": mapped.get('name_latin'),
        "common_name_en": mapped.get('common_name_en'),
        "family": mapped.get('family'),
        "genus": mapped.get('genus'),
        "category": "蛋龟",
        "morph": "原种",
        "morph_tier": None,
        "size_max_cm": mapped.get('size_max_cm'),
        "lifespan_years": mapped.get('lifespan_years'),
        "distribution": mapped.get('distribution'),
        "conservation": mapped.get('conservation'),
        "cites": mapped.get('cites'),
        "difficulty": mapped.get('difficulty'),
        "temp_range": mapped.get('temp_range'),
        "price_range": None,
        "key_traits": key_traits,
        "overview": summary[:400] if summary else '',
        "source": "百度百科",
        "source_url": f"https://baike.baidu.com/item/{name_cn}",
        # DB 兼容字段
        "traits": {
            "壳形": "椭圆形" if '龙骨背甲' not in key_traits else "高隆棱脊",
            "头纹": "",
            "色泽": "",
        },
        "care_params": {
            "温度": mapped.get('temp_range') or "22-28°C",
            "湿度": "70-85%",
            "光照": "UVB 5.0 每天6-8h",
            "食物": "龟粮+小鱼虾",
            "冬眠": "不推荐",
        },
    }

    # 置信度计算：统计非空/非null字段
    score_fields = ['name_latin', 'family', 'genus', 'distribution', 'conservation',
                    'size_max_cm', 'lifespan_years', 'temp_range']
    filled = sum(1 for f in score_fields if result.get(f))
    result['_confidence'] = round(filled / len(score_fields) * 100)

    return result


def main():
    results = []
    total = len(SPECIES_LIST)

    print(f"🐢 开始爬取 {total} 个蛋龟品种...\n")

    for i, name_cn in enumerate(SPECIES_LIST, 1):
        print(f"[{i}/{total}] {name_cn} ...", end=' ', flush=True)

        html = fetch_page(name_cn)
        if not html:
            print("❌ 页面不存在")
            results.append({"name_cn": name_cn, "error": "page_not_found"})
            continue

        raw = parse_baike(html)
        species = extract_fields(raw, name_cn)
        results.append(species)

        conf = species['_confidence']
        icon = "✅" if conf >= 50 else "⚠️" if conf >= 25 else "❌"
        print(f"{icon} (置信度 {conf}% | 学名={species.get('name_latin','?')})")

        if i < total:
            time.sleep(REQUEST_DELAY)

    # 写入 JSON
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 统计
    success = sum(1 for r in results if 'error' not in r)
    fail = sum(1 for r in results if 'error' in r)
    avg_conf = sum(r.get('_confidence', 0) for r in results if 'error' not in r) / max(success, 1)

    print(f"\n{'='*50}")
    print(f"📄 {OUTPUT_FILE}")
    print(f"   总数: {total} | 成功: {success} | 失败: {fail} | 平均置信度: {avg_conf:.0f}%")


if __name__ == '__main__':
    main()
