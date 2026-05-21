#!/usr/bin/env python3
"""
B站视频训练图采集 — 搜品种名 → 下载视频 → 抽帧 → 入训练集
用法：
  python3 scripts/bili_training_scraper.py                    # 全量368种
  python3 scripts/bili_training_scraper.py --species 75       # 单品种
  python3 scripts/bili_training_scraper.py --species 75 79 68 # 多品种
  python3 scripts/bili_training_scraper.py --max-videos 3     # 每种最多3个视频
"""
import os, sys, json, time, sqlite3, subprocess, tempfile, re, argparse, hashlib
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'data' / 'digeguigui.db'
OUT_DIR = BASE_DIR / 'data' / 'training' / 'bili_v2'
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = Path('/tmp/bili_training')
TMP_DIR.mkdir(exist_ok=True)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def bili_api(path, params='', max_retries=3):
    """B站API，带重试和反反爬"""
    url = f'https://api.bilibili.com/x/web-interface{path}?{params}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/',
        'Origin': 'https://www.bilibili.com',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cookie': 'buvid3=auto; fingerprint=auto',
    }
    for attempt in range(max_retries):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
                if data.get('code') != 0:
                    # B站业务错误，可重试
                    if attempt < max_retries - 1:
                        time.sleep(1 + attempt * 2)
                        continue
                return data
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1 + attempt * 2)
                continue
            print(f"  ⚠ B站API失败(重试{max_retries}次): {e}")
            return None
    return None

def search_videos(keyword, max_results=5):
    """搜B站视频，返回 [(bvid, title, duration), ...]"""
    results = []
    for page in range(1, 3):
        data = bili_api('/search/type', f'search_type=video&keyword={quote(keyword)}&page={page}&order=click')
        if not data or data.get('code') != 0:
            break
        for v in data.get('data', {}).get('result', []):
            bvid = v.get('bvid', '')
            title = v.get('title', '').replace('<em class="keyword">', '').replace('</em>', '')
            duration = v.get('duration', '0:0')
            # 过滤太短或太长的视频
            dur_sec = sum(int(x) * (60**i) for i, x in enumerate(reversed(duration.split(':')))) if duration else 999
            if dur_sec < 30:  # 少于30秒跳过
                continue
            if dur_sec > 900:  # 超过15分钟跳过
                continue
            results.append((bvid, title, duration))
            if len(results) >= max_results:
                break
        if len(results) >= max_results:
            break
        time.sleep(0.5)
    return results

def bili_api_raw(url, max_retries=3):
    """B站API原始调用，不拼前缀（用于非 /x/web-interface 端点）"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/',
        'Origin': 'https://www.bilibili.com',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cookie': 'buvid3=auto; fingerprint=auto',
    }
    for attempt in range(max_retries):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
                if data.get('code') != 0:
                    if attempt < max_retries - 1:
                        time.sleep(1 + attempt * 2)
                        continue
                return data
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1 + attempt * 2)
                continue
            print(f"  ⚠ B站API失败(重试{max_retries}次): {e}")
            return None
    return None

def get_video_url(bvid):
    """获取B站视频直链（最高画质）"""
    # 先获取cid
    data = bili_api('/view', f'bvid={bvid}')
    if not data or data.get('code') != 0:
        return None
    
    cid = data['data'].get('cid', 0)
    aid = data['data'].get('aid', 0)
    
    # 获取播放地址（playurl 端点路径不同：/x/player/playurl）
    play = bili_api_raw(f'https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=80&fnval=1')
    if not play or play.get('code') != 0:
        return None
    
    durl = play.get('data', {}).get('durl', [])
    if not durl:
        return None
    
    return durl[0].get('url', ''), aid, cid

def fetch_comments(aid, max_pages=3):
    """爬B站评论区，返回口语化特征文本"""
    comments = []
    for pn in range(1, max_pages + 1):
        url = f'https://api.bilibili.com/x/v2/reply?type=1&oid={aid}&pn={pn}&sort=1'
        data = bili_api_raw(url)
        if not data or data.get('code') != 0:
            break
        for reply in (data.get('data') or {}).get('replies') or []:
            msg = reply.get('content', {}).get('message', '')
            if msg and len(msg) > 5:
                comments.append(msg)
        if not data.get('data', {}).get('replies'):
            break
        time.sleep(0.5)
    return comments

COMMENT_DIR = Path('/home/ubuntu/digeguigui/data/comments')
COMMENT_DIR.mkdir(parents=True, exist_ok=True)

def download_video(bvid, out_path):
    """下载B站视频，返回 (成功, aid)"""
    result = get_video_url(bvid)
    if not result:
        return False, None
    url, aid, cid = result
    if not url:
        return False, aid
    
    req = Request(url, headers={
        'User-Agent': USER_AGENT,
        'Referer': f'https://www.bilibili.com/video/{bvid}',
    })
    try:
        with urlopen(req, timeout=120) as r:
            with open(out_path, 'wb') as f:
                f.write(r.read())
        return True, aid
    except Exception as e:
        print(f"    下载失败 {bvid}: {e}")
        return False, aid

def extract_frames(video_path, output_dir, interval=3):
    """抽帧：每隔 interval 秒抽一帧"""
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        'ffmpeg', '-i', str(video_path),
        '-vf', f'fps=1/{interval},scale=640:-1',
        '-q:v', '2',  # 高质量
        '-y',  # 覆盖
        str(output_dir / 'frame_%04d.jpg')
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
        return len(list(output_dir.glob('frame_*.jpg')))
    except:
        return 0

def process_species(species_id, name_cn, name_latin, max_videos=3):
    """处理单个品种"""
    sp_dir = OUT_DIR / f'{species_id:04d}'
    sp_dir.mkdir(parents=True, exist_ok=True)
    
    existing = len(list(sp_dir.glob('*.jpg')))
    if existing >= 200:
        print(f"  [{species_id}] {name_cn}: ✅ 已有{existing}张，跳过")
        return existing
    
    # 搜索关键词
    keywords = [name_cn]
    # 加简称
    if '龟' in name_cn:
        keywords.append(name_cn.replace('龟', ''))
    genus = name_latin.split()[0] if name_latin else ''
    
    all_videos = []
    for kw in keywords[:2]:
        vids = search_videos(f'{kw} 龟', max_results=max_videos)
        all_videos.extend(vids)
        time.sleep(0.3)
    
    # 去重
    seen = set()
    unique = []
    for bvid, title, dur in all_videos:
        if bvid not in seen:
            seen.add(bvid)
            unique.append((bvid, title, dur))
    
    total_new = 0
    for bvid, title, dur in unique[:max_videos]:
        # 跳过已处理的
        marker = sp_dir / f'.{bvid}'
        if marker.exists():
            continue
        
        tmp_video = TMP_DIR / f'{bvid}.mp4'
        tmp_frames = TMP_DIR / f'frames_{bvid}'
        
        print(f"    下载 {bvid} ({dur}) - {title[:30]}...", end=' ', flush=True)
        success, aid = download_video(bvid, tmp_video)
        if success:
            n = extract_frames(tmp_video, tmp_frames, interval=2)
            # 移到品种目录
            for f in tmp_frames.glob('frame_*.jpg'):
                h = hashlib.md5(bvid.encode() + f.name.encode()).hexdigest()[:8]
                f.rename(sp_dir / f'{h}.jpg')
            total_new += n
            print(f'{n}帧', end='')
            # 清理
            tmp_video.unlink(missing_ok=True)
            for f in tmp_frames.glob('*.jpg'):
                f.unlink(missing_ok=True)
            tmp_frames.rmdir()
            marker.touch()
        else:
            print('失败', end='')
        
        # 🗣️ 爬评论（不管下载成不成功，有aid就爬）
        if aid:
            comments = fetch_comments(aid, max_pages=2)
            if comments:
                comment_file = COMMENT_DIR / f'{species_id:04d}_{name_cn}_{bvid}.txt'
                comment_file.write_text('\n---\n'.join(comments), encoding='utf-8')
                print(f' +{len(comments)}评', end='')
        print()
        time.sleep(1)
    
    total = existing + total_new
    if total_new > 0:
        print(f"  [{species_id}] {name_cn}: +{total_new}帧 → 共{total}张")
    
    return total

def main():
    parser = argparse.ArgumentParser(description='B站视频训练图采集')
    parser.add_argument('--species', type=int, nargs='*', help='指定品种ID')
    parser.add_argument('--max-videos', type=int, default=3, help='每种最多下载视频数')
    parser.add_argument('--min-existing', type=int, default=100, help='已有≥此数值时跳过')
    args = parser.parse_args()
    
    conn = sqlite3.connect(DB_PATH)
    if args.species:
        placeholders = ','.join('?' * len(args.species))
        rows = conn.execute(
            f"SELECT species_id, name_cn, name_latin FROM species WHERE species_id IN ({placeholders})",
            args.species
        ).fetchall()
    else:
        # 全量：按现有训练图数量排序，优先补缺
        rows = conn.execute("""
            SELECT species_id, name_cn, name_latin FROM species WHERE category='龟' ORDER BY species_id
        """).fetchall()
    conn.close()
    
    print(f"🎬 B站训练图采集 — {len(rows)} 种龟 | 每种 ≤{args.max_videos} 视频\n")
    
    total_frames = 0
    for row in rows:
        n = process_species(row[0], row[1], row[2], max_videos=args.max_videos)
        total_frames += n
    
    print(f"\n{'='*50}")
    print(f"总帧数: {total_frames}")
    print(f"输出: {OUT_DIR}")

if __name__ == '__main__':
    main()
