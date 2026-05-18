#!/usr/bin/env python3
"""
B站爬宠视频 → 训练图提取管线
用 B站 API (无需 yt-dlp) 搜索+下载+抽帧+去重

用法:
  python3 scripts/bili_pipeline.py 巴西龟
  python3 scripts/bili_pipeline.py --search "剃刀龟 饲养"
  python3 scripts/bili_pipeline.py --batch top20      # 批量处理高频20种
"""

import json, os, sys, re, time, shutil, hashlib, subprocess
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request, urlretrieve
from urllib.parse import quote

PROJ = os.path.expanduser("~/digeguigui")
DATASET = "/tmp/turtle_dataset"
TMP = "/tmp/bili_frames"
MAX_VIDEOS_PER_SPECIES = 5
MAX_FRAMES_PER_VIDEO = 30
SCENE_THRESHOLD = 0.25
DEDUP_THRESHOLD = 8  # perceptual hash hamming distance

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REFERER = "https://www.bilibili.com"

# ── 高频龟种搜索词 ──
SPECIES_SEARCH = {
    "巴西龟": ["巴西龟 饲养", "红耳龟 怎么养", "巴西龟苗 饲养环境"],
    "草龟": ["草龟 饲养", "中华草龟 怎么养", "草龟苗 环境"],
    "麝香龟": ["麝香龟 饲养", "麝香蛋龟", "麝香龟 环境"],
    "剃刀龟": ["剃刀龟 饲养", "剃刀蛋龟", "剃刀龟 环境布置"],
    "地图龟": ["地图龟 饲养", "密西西比地图龟", "地图龟 深水"],
    "鳄龟": ["鳄龟 饲养", "佛鳄龟", "北美鳄龟 怎么养"],
    "猪鼻龟": ["猪鼻龟 饲养", "猪鼻龟 深水缸"],
    "黄缘": ["黄缘闭壳龟 饲养", "黄缘龟 环境", "黄缘 冬眠"],
    "黄喉": ["黄喉拟水龟", "南石龟 饲养", "黄喉 发色"],
    "钻纹": ["钻纹龟 饲养", "钻纹 汽水"],
    "苏卡达": ["苏卡达陆龟 饲养", "苏卡达 排酸", "苏卡达 环境"],
    "豹纹陆龟": ["豹纹陆龟 饲养", "豹纹龟 吃什么"],
    "红腿": ["红腿陆龟 饲养", "红腿 环境"],
    "亚达": ["亚达伯拉象龟", "亚达 饲养环境"],
    "东锦": ["东锦龟 饲养", "锦龟 环境布置"],
    "西锦": ["西锦龟 饲养", "锦龟 冬眠"],
    "箱龟": ["东部箱龟 饲养", "箱龟 环境", "箱龟 冬眠"],
    "木雕": ["木雕水龟 饲养", "北美木雕龟"],
    "果核蛋龟": ["果核蛋龟 饲养", "果核泥龟"],
    "巨头蛋龟": ["巨头蛋龟 饲养", "巨头麝香龟"],
    "白唇蛋龟": ["白唇蛋龟 饲养", "白唇泥龟"],
    "虎纹蛋龟": ["虎纹蛋龟 饲养", "虎纹麝香龟"],
    "窄桥蛋龟": ["窄桥蛋龟 饲养", "窄桥匣龟"],
    "萨尔文蛋龟": ["萨尔文蛋龟 饲养", "萨尔文巨蛋"],
    "墨西哥蛋龟": ["墨西哥蛋龟 饲养", "墨蛋 环境"],
    "平背": ["平背麝香龟", "平背蛋龟"],
    "斑点池龟": ["斑点池龟 饲养", "黑池龟"],
    "鹰嘴龟": ["鹰嘴龟 饲养", "大头平胸龟"],
    "枫叶龟": ["枫叶龟 饲养", "地龟 环境"],
    "金钱龟": ["金钱龟 饲养", "三线闭壳龟"],
}

def api_get(url, params=None):
    """B站 API GET, returns parsed JSON."""
    full_url = url
    if params:
        qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        full_url = f"{url}?{qs}"
    
    req = Request(full_url, headers={"User-Agent": UA, "Referer": REFERER})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"    ⚠️ API error: {e}")
        return None

def search_videos(keyword, max_results=20):
    """Search B站 for videos."""
    data = api_get("https://api.bilibili.com/x/web-interface/search/all/v2", 
                   {"keyword": keyword, "page": 1, "search_type": "video"})
    if not data or data.get("code") != 0:
        return []
    
    results = data.get("data", {}).get("result", [])
    videos = []
    for item in results:
        if isinstance(item, dict) and item.get("result_type") == "video":
            for v in item.get("data", []):
                # 过滤太短(广告)或太长(电影)的视频
                dur = v.get("duration", "0:00")
                parts = dur.split(":")
                seconds = int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else 0
                if seconds < 60 or seconds > 1800:
                    continue
                
                # 清理标题中的HTML标签
                title = re.sub(r'<[^>]+>', '', v.get("title", ""))
                
                videos.append({
                    "bvid": v.get("bvid"),
                    "aid": v.get("aid"),
                    "title": title,
                    "author": v.get("author"),
                    "duration": seconds,
                    "play": v.get("play", 0),
                    "url": f"https://www.bilibili.com/video/{v.get('bvid')}",
                })
    
    return videos[:max_results]

def get_video_info(bvid):
    """Get video details + cid."""
    data = api_get("https://api.bilibili.com/x/web-interface/view", {"bvid": bvid})
    if not data or data.get("code") != 0:
        return None
    
    info = data["data"]
    pages = info.get("pages", [{"cid": info.get("cid")}])
    
    return {
        "bvid": bvid,
        "title": info.get("title", ""),
        "duration": info.get("duration", 0),
        "cid": pages[0].get("cid") if pages else info.get("cid"),
        "has_subtitle": info.get("subtitle", {}).get("allow_submit", False),
    }

def get_download_url(bvid, cid):
    """Get video CDN download URL."""
    data = api_get("https://api.bilibili.com/x/player/playurl",
                   {"bvid": bvid, "cid": cid, "qn": 80, "fnval": 1, "fourk": 1})
    if not data or data.get("code") != 0:
        return None
    
    durl = data.get("data", {}).get("durl", [])
    if durl:
        return durl[0]["url"].replace("\\u0026", "&")
    return None

def download_video(url, output_path):
    """Download video from B站 CDN."""
    try:
        req = Request(url, headers={"User-Agent": UA, "Referer": REFERER})
        with urlopen(req, timeout=120) as resp:
            with open(output_path, "wb") as f:
                shutil.copyfileobj(resp, f)
        return os.path.getsize(output_path) > 10000  # >10KB
    except Exception as e:
        print(f"    ⚠️ Download failed: {e}")
        return False

def extract_frames(video_path, output_dir, prefix="frame"):
    """ffmpeg scene change detection → key frames."""
    os.makedirs(output_dir, exist_ok=True)
    fname = os.path.join(output_dir, f"{prefix}_%04d.jpg")
    
    cmd = (
        f'ffmpeg -i "{video_path}" '
        f'-vf "select=gt(scene\\,{SCENE_THRESHOLD}),scale=640:-1" '
        f'-vsync vfr -q:v 3 '
        f'-frames:v {MAX_FRAMES_PER_VIDEO * 2} '
        f'"{fname}" -y -loglevel error'
    )
    subprocess.run(cmd, shell=True, timeout=60)
    
    return sorted(Path(output_dir).glob(f"{prefix}_*.jpg"))

def deduplicate_frames(frames, threshold=DEDUP_THRESHOLD):
    """Perceptual hash dedup."""
    if len(frames) <= 1:
        return frames
    
    try:
        from PIL import Image
        import imagehash
    except ImportError:
        print("    ⚠️ PIL/imagehash not available, skipping dedup")
        return frames[:MAX_FRAMES_PER_VIDEO]
    
    frame_hashes = []
    for f in frames:
        try:
            h = imagehash.average_hash(Image.open(f))
            frame_hashes.append((f, h))
        except:
            continue
    
    if not frame_hashes:
        return frames[:MAX_FRAMES_PER_VIDEO]
    
    kept = [frame_hashes[0]]
    for frame, h in frame_hashes[1:]:
        if all(abs(h - kh) > threshold for _, kh in kept):
            kept.append((frame, h))
    
    return [f for f, _ in kept][:MAX_FRAMES_PER_VIDEO]

def process_species(species_name, search_queries=None):
    """Full pipeline for one species via B站."""
    if search_queries is None:
        search_queries = SPECIES_SEARCH.get(species_name, [species_name + " 饲养"])
    
    print(f"\n🐢 [{species_name}]")
    
    # Phase 1: Search
    all_videos = []
    for query in search_queries:
        print(f"  🔍 搜索: {query}")
        vids = search_videos(query)
        all_videos.extend(vids)
        time.sleep(1)
    
    # Dedup
    seen = set()
    unique = []
    for v in all_videos:
        if v["bvid"] not in seen:
            seen.add(v["bvid"])
            unique.append(v)
    
    print(f"  📺 找到 {len(unique)} 个视频")
    if not unique:
        return 0
    
    # Phase 2: Download + Extract
    tmp_dir = os.path.join(TMP, species_name.replace(" ", "_"))
    os.makedirs(tmp_dir, exist_ok=True)
    
    total_saved = 0
    processed = 0
    
    for video in unique:
        if processed >= MAX_VIDEOS_PER_SPECIES:
            break
        
        # Get video info + cid
        info = get_video_info(video["bvid"])
        if not info or not info.get("cid"):
            continue
        
        print(f"    📥 {video['title'][:50]}... ({video['duration']}s)")
        
        # Get download URL
        dl_url = get_download_url(video["bvid"], info["cid"])
        if not dl_url:
            print(f"    ⚠️ 无法获取下载地址")
            continue
        
        # Download
        video_path = os.path.join(tmp_dir, f"{video['bvid']}.mp4")
        if not os.path.exists(video_path):
            if not download_video(dl_url, video_path):
                continue
        
        # Extract frames
        frame_dir = os.path.join(tmp_dir, f"frames_{video['bvid']}")
        frames = extract_frames(video_path, frame_dir)
        print(f"    🎬 抽帧: {len(frames)} candidates")
        
        # Dedup
        unique_frames = deduplicate_frames(frames)
        print(f"    🔍 去重: {len(frames)} → {len(unique_frames)} unique")
        
        # Save to dataset
        species_dir = os.path.join(DATASET, species_name)
        os.makedirs(species_dir, exist_ok=True)
        
        existing = len(list(Path(species_dir).glob("bili_*.jpg")))
        saved = 0
        for i, frame in enumerate(unique_frames):
            dest = os.path.join(species_dir, f"bili_{existing + i:04d}.jpg")
            if not os.path.exists(dest):
                shutil.copy(frame, dest)
                saved += 1
        
        print(f"    ✅ 入库 {saved} 张")
        total_saved += saved
        processed += 1
        
        # Cleanup video
        try:
            os.remove(video_path)
        except:
            pass
        
        time.sleep(2)
    
    # Save metadata
    meta = {
        "source": "bilibili",
        "date": datetime.now().isoformat(),
        "species": species_name,
        "total_images": total_saved,
        "videos_processed": processed,
    }
    species_dir = os.path.join(DATASET, species_name)
    os.makedirs(species_dir, exist_ok=True)
    with open(os.path.join(species_dir, "bili_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    
    print(f"  📊 [{species_name}] 合计: {total_saved} 张训练图 (来自 {processed} 个视频)")
    return total_saved

def main():
    args = sys.argv[1:]
    
    if not args or args[0] in ("--help", "-h"):
        print("B站爬宠视频 → 训练图管线")
        print()
        print("用法:")
        print("  python3 scripts/bili_pipeline.py 巴西龟")
        print("  python3 scripts/bili_pipeline.py --search '剃刀龟 饲养'")
        print("  python3 scripts/bili_pipeline.py --batch top10")
        print("  python3 scripts/bili_pipeline.py --list")
        print("  python3 scripts/bili_pipeline.py --cron    # 巡检模式：每种只下一个视频")
        return
    
    if args[0] == "--list":
        print("已配置品种:")
        for name in SPECIES_SEARCH:
            print(f"  {name}")
        return
    
    if args[0] == "--search":
        query = " ".join(args[1:])
        print(f"🔍 搜索: {query}")
        vids = search_videos(query, 10)
        for v in vids:
            print(f"  [{v['duration']}s | {v['play']}播放] {v['title'][:60]}")
            print(f"    {v['url']} | UP: {v['author']}")
        return
    
    if args[0] == "--batch":
        # 批量模式
        count = int(args[1].replace("top", "")) if len(args) > 1 and args[1].startswith("top") else 10
        species_list = list(SPECIES_SEARCH.items())[:count]
        
        print(f"🚀 批量处理 {len(species_list)} 种龟...")
        total = 0
        for name, _ in species_list:
            saved = process_species(name)
            total += saved
        
        print(f"\n✅ 完成. {total} 张训练图 ({len(species_list)} 品种)")
        return
    
    if args[0] == "--cron":
        # 巡检模式：快速扫一轮，每种只下一个视频
        species_list = list(SPECIES_SEARCH.items())
        print(f"🕐 巡检模式: {len(species_list)} 种")
        total = 0
        global MAX_VIDEOS_PER_SPECIES
        MAX_VIDEOS_PER_SPECIES = 1
        for name, _ in species_list:
            saved = process_species(name)
            total += saved
        print(f"\n✅ 巡检: {total} 张新图")
        return
    
    # 单品种模式
    species_name = " ".join(args)
    # 模糊匹配
    for key in SPECIES_SEARCH:
        if species_name in key or key in species_name:
            process_species(key)
            return
    
    # 直接搜索
    process_species(species_name, [species_name + " 饲养", species_name + " 龟"])

if __name__ == "__main__":
    main()
