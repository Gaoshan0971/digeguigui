#!/usr/bin/env python3
"""B站龟类价格视频 → 结构化价格数据管线
用法：python3 bili_price_pipeline.py BV1q7RvBFE5i          # 单视频
      python3 bili_price_pipeline.py --batch                # 批量跑已知价格视频
      python3 bili_price_pipeline.py --search "蛋龟 行情"   # 搜索+下载+提取
"""
import requests, json, base64, os, re, sqlite3, subprocess, tempfile, argparse, time

HUNYUAN_KEY = 'sk-9W9gW9vKBlRumlofaDl3g104nKh8iTsQVrhzirEx2lo2lGvU'
DB_PATH = '/home/ubuntu/digeguigui/data/digeguigui.db'
TMP_DIR = '/tmp/bili_prices'

# ── 俗名→species_id 映射 ──
NAME_MAP = {
    # Sternotherus (麝香龟属)
    '麝香蛋龟': 58, '麝香龟': 58, '密西西比麝香龟': 58,
    '剃刀蛋龟': 57, '剃刀龟': 57, '剃刀麝香龟': 57,
    '巨头蛋龟': 59, '巨头麝香龟': 59,
    '虎纹蛋龟': 81, '虎纹麝香龟': 81, '条颈麝香龟': 81, '条颈麝香龟（虎纹）': 81,
    # Kinosternon (动胸龟属/泥龟属)
    '果核蛋龟': 64, '果核泥龟': 64, '条纹动胸龟': 64, '条纹动胸龟（果核）': 64,
    '国产红面': 62, '红面蛋龟': 62, '红面泥龟': 62, '国产红面蛋龟': 62,
    '白唇蛋龟': 61, '白唇泥龟': 61, '白唇动胸龟': 61,
    '黄泽蛋龟': 296, '黄泽': 296, '黄泽动胸龟': 296,
    '东方蛋龟': 63, '东方泥龟': 63, '头盔泥龟': 63,
    '斑纹蛋龟': 286, '斑纹动胸龟': 286,
    # Staurotypus (大麝香龟属)
    '墨西哥蛋龟': 103, '墨西哥巨蛋': 103, '墨西哥大麝香龟': 103,
    '萨尔文蛋龟': 104, '萨尔文': 104, '萨尔文大麝香龟': 104,
    # Claudius (匣龟属)
    '窄桥蛋龟': 66, '鹰嘴泥龟': 66, '窄桥匣龟': 66,
    # 常见水龟/陆龟
    '草龟': 68, '中华草龟': 68,
    '花龟': 80, '中华花龟': 80, '珍珠龟': 80,
    '巴西龟': 774, '红耳龟': 774,
    '黄喉': 79, '黄喉拟水龟': 79,
    '黄缘': 67, '黄缘闭壳龟': 67,
    '钻纹': 72, '钻纹龟': 72,
    '大鳄龟': 75, '大鳄': 75,
    '鳄龟': 74, '小鳄龟': 74,
    '猪鼻龟': 71, '猪鼻': 71,
    '地图龟': 82, '地图': 82,
    '东锦龟': 83, '东锦': 83,
    '西锦龟': 775, '西锦': 775,
    '苏卡达': 70, '苏卡达陆龟': 70,
    '豹纹陆龟': 69, '豹纹': 69,
    '亚达': 107, '亚达伯拉': 107,
    '锯缘龟': 96, '锯缘摄龟': 96, '锯缘': 96, 'CB锯缘苗': 96, '锯缘苗': 96,
    '黄头': 112, '黄头侧颈龟': 112,
    '枫叶龟': 93,
}

# ── 已知价格视频 ──
KNOWN_PRICE_VIDEOS = [
    ('BV1q7RvBFE5i', '2026年5月蛋龟苗批发价'),
    ('BV1nS516qE3D', '五月热门蛋龟市场价'),
    ('BV16LR6Y4ETV', '2025年4月蛋龟苗价格'),
    ('BV1ASHreTEej', '蛋龟苗九月份出苗季行情'),
    ('BV1hT411V7k6', '草龟多少钱一只'),
    ('BV1WXenzTEdR', '金线草龟苗价格'),
    ('BV1dV411o7Y9', '鳄龟科价格参考'),
    ('BV1DUqqYxEEP', '钻纹龟价格'),
    ('BV1Vg411P7Bz', '猪鼻龟价格'),
    ('BV18w411A721', '锯缘价格暴跌'),
    ('BV1ioiKBNESn', '2026蛋龟价格预测'),
    ('BV1Z7QrBkECT', '2026蛋龟市场分析'),
]


def download_video(bvid):
    """下载B站视频 → 本地mp4"""
    os.makedirs(TMP_DIR, exist_ok=True)
    outpath = f'{TMP_DIR}/{bvid}.mp4'
    if os.path.exists(outpath):
        return outpath
    
    info = requests.get(f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}',
                         headers={'Referer': 'https://www.bilibili.com', 'User-Agent': 'Mozilla/5.0'}).json()['data']
    cid = info['cid']
    play = requests.get(f'https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=80&fnval=1',
                         headers={'Referer': 'https://www.bilibili.com', 'User-Agent': 'Mozilla/5.0'}).json()['data']
    url = play['durl'][0]['url']
    r = requests.get(url, headers={'Referer': 'https://www.bilibili.com', 'User-Agent': 'Mozilla/5.0'})
    with open(outpath, 'wb') as f:
        f.write(r.content)
    print(f'  下载: {bvid} ({len(r.content)/1024:.0f}KB)')
    return outpath


def extract_frames(video_path, interval=2):
    """场景检测抽帧"""
    frame_dir = video_path.replace('.mp4', '_frames')
    os.makedirs(frame_dir, exist_ok=True)
    # Clear old frames
    for f in os.listdir(frame_dir):
        os.remove(f'{frame_dir}/{f}')
    subprocess.run(['ffmpeg', '-i', video_path, '-vf', f'fps=1/{interval}', '-q:v', '3',
                    f'{frame_dir}/frame_%03d.jpg', '-y'], 
                   capture_output=True)
    frames = sorted(os.listdir(frame_dir))
    return [f'{frame_dir}/{f}' for f in frames]


def read_frame_hunyuan(frame_path):
    """混元视觉读帧中的价格信息"""
    b64 = base64.b64encode(open(frame_path, 'rb').read()).decode()
    resp = requests.post('https://api.hunyuan.cloud.tencent.com/v1/chat/completions',
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {HUNYUAN_KEY}'},
        json={
            'model': 'hunyuan-turbos-vision',
            'messages': [{
                'role': 'user',
                'content': [
                    {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
                    {'type': 'text', 'text': '提取图中所有龟类品种名和对应价格。格式：品种名=价格。没有价格信息回复"无价格"。'}
                ]
            }],
            'max_tokens': 300, 'temperature': 0.1
        }, timeout=25)
    
    if resp.status_code == 200:
        return resp.json()['choices'][0]['message']['content']
    return ''


def parse_prices(text):
    """解析 '品种名=价格' 行"""
    prices = {}
    for line in text.strip().split('\n'):
        # Match '品种名=价格' or '品种名=价格元' or '品种名：价格'
        m = re.match(r'(.+?)[=＝:：]\s*(\d+)', line.strip())
        if m:
            name, price = m.group(1).strip(), int(m.group(2))
            # Filter noise
            if price > 0 and price < 100000 and len(name) < 20 and '价格' not in name:
                prices[name] = price
    return prices


def import_to_db(prices, source):
    """去重后入库"""
    db = sqlite3.connect(DB_PATH)
    count = 0
    for name, price in prices.items():
        sid = NAME_MAP.get(name)
        if not sid:
            print(f'    ⚠️ 未映射: {name}=¥{price}')
            continue
        
        sp = db.execute('SELECT name_cn FROM species WHERE species_id = ?', (sid,)).fetchone()
        if not sp:
            continue
        
        result = db.execute('''
            UPDATE species_prices 
            SET normal_low = ?, normal_high = ?, price_note = ?, updated_at = datetime('now','localtime')
            WHERE species_id = ?
        ''', (price, price, f'B站价格视频 {source}', sid))
        
        if result.rowcount == 0:
            db.execute('''
                INSERT INTO species_prices (species_id, normal_low, normal_high, price_note)
                VALUES (?, ?, ?, ?)
            ''', (sid, price, price, f'B站价格视频 {source}'))
        
        print(f'    ✅ {sp[0]} = ¥{price}')
        count += 1
    
    db.commit()
    db.close()
    return count


def process_video(bvid, label=''):
    """完整管线：下载→抽帧→读价→入库"""
    print(f'\n🎬 {label or bvid}')
    try:
        video = download_video(bvid)
        frames = extract_frames(video)
        print(f'  抽帧: {len(frames)} 张 ({len(frames)*2}s 间隔)')
        
        all_prices = {}
        for i, fp in enumerate(frames):
            text = read_frame_hunyuan(fp)
            if text and '无价格' not in text:
                prices = parse_prices(text)
                all_prices.update(prices)
            if i % 5 == 0:
                print(f'  进度: {i+1}/{len(frames)}')
            time.sleep(0.5)  # rate limit
        
        if all_prices:
            source = f'{bvid} {label}' if label else bvid
            count = import_to_db(all_prices, source)
            print(f'  入库: {count} 条')
        else:
            print('  未找到价格数据')
        return len(all_prices)
    except Exception as e:
        print(f'  ❌ 失败: {e}')
        return 0


def search_videos(keyword, count=5):
    """搜索B站价格视频"""
    resp = requests.get(
        f'https://api.bilibili.com/x/web-interface/search/all/v2?keyword={keyword}&page=1&page_size={count}',
        headers={'Referer': 'https://www.bilibili.com', 'User-Agent': 'Mozilla/5.0'}
    )
    data = resp.json()
    videos = []
    for r in data.get('data', {}).get('result', []):
        if r.get('result_type') == 'video':
            for v in r.get('data', []):
                videos.append((v['bvid'], v['title'].replace('<em class="keyword">', '').replace('</em>', '')))
    return videos


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('bvid', nargs='?', help='单视频 BV号')
    parser.add_argument('--label', default='', help='视频标签')
    parser.add_argument('--batch', action='store_true', help='批量跑已知价格视频')
    parser.add_argument('--search', help='搜索关键词')
    parser.add_argument('--interval', type=int, default=2, help='抽帧间隔(秒)')
    args = parser.parse_args()
    
    if args.search:
        videos = search_videos(args.search)
        print(f'搜索 "{args.search}": {len(videos)} 个视频')
        for bvid, title in videos:
            print(f'  {bvid}: {title[:60]}')
        if videos and input('\n下载并提取? (y/n): ').lower() == 'y':
            for bvid, title in videos:
                process_video(bvid, title)
    
    elif args.batch:
        total = 0
        for bvid, label in KNOWN_PRICE_VIDEOS:
            n = process_video(bvid, label)
            total += n
            time.sleep(2)
        print(f'\n📊 总计提取: {total} 条价格')
    
    elif args.bvid:
        process_video(args.bvid, args.label)
    
    else:
        parser.print_help()
