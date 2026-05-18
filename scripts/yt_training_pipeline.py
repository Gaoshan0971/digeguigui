#!/usr/bin/env python3
"""
YouTube 爬宠视频 → 训练图提取管线
用法: python3 scripts/yt_training_pipeline.py [species_name|all|--search "keyword"]

流程:
1. yt-dlp 搜索/下载视频
2. ffmpeg 提取关键帧（场景变化检测）
3. 去重（感知哈希 > 阈值 → 丢弃）
4. 保存到 /tmp/turtle_dataset/{species}/

依赖: yt-dlp, ffmpeg, pip install Pillow imagehash
"""

import os, sys, json, hashlib, subprocess, time, shutil, re
from pathlib import Path
from datetime import datetime

PROJ = os.path.expanduser("~/digeguigui")
DATASET = "/tmp/turtle_dataset"
TMP = "/tmp/yt_frames"
MAX_VIDEOS_PER_SPECIES = 5
MAX_FRAMES_PER_VIDEO = 30   # after dedup
SCENE_THRESHOLD = 0.25      # ffmpeg scene change sensitivity
DEDUP_THRESHOLD = 8         # perceptual hash hamming distance

# ── 品种搜索词映射 ──
SPECIES_SEARCH = {
    # 高频流通品种 → YouTube 搜索词
    "巴西龟": ["red eared slider turtle care", "red eared slider unboxing", "turtle setup red eared slider"],
    "草龟": ["chinese pond turtle care", "Mauremys reevesii", "草龟 饲养"],
    "麝香龟": ["musk turtle care", "stinkpot turtle", "Sternotherus odoratus"],
    "剃刀龟": ["razorback musk turtle", "Sternotherus carinatus care"],
    "地图龟": ["mississippi map turtle care", "Graptemys turtle"],
    "鳄龟": ["snapping turtle care", "common snapping turtle", "Chelydra serpentina"],
    "猪鼻龟": ["fly river turtle care", "Carettochelys insculpta"],
    "黄缘": ["chinese box turtle care", "Cuora flavomarginata", "黄缘闭壳龟"],
    "黄喉": ["asian yellow pond turtle", "Mauremys mutica"],
    "钻纹": ["diamondback terrapin care", "Malaclemys terrapin"],
    "红腿": ["red footed tortoise care", "Chelonoidis carbonarius"],
    "苏卡达": ["sulcata tortoise care", "Centrochelys sulcata", "苏卡达陆龟"],
    "豹纹陆龟": ["leopard tortoise care", "Stigmochelys pardalis"],
    "亚达": ["aldabra tortoise", "Aldabrachelys gigantea"],
    "东锦": ["eastern painted turtle", "Chrysemys picta"],
    "西锦": ["western painted turtle care"],
    "箱龟": ["eastern box turtle care", "Terrapene carolina"],
    "木雕": ["wood turtle care", "Glyptemys insculpta"],
    "蛋龟": ["mud turtle care", "musk turtle care", "Kinosternon", "Sternotherus"],
    "白化巴西": ["albino red eared slider", "albino turtle"],
    "果核蛋龟": ["striped mud turtle", "Kinosternon baurii"],
    "巨头蛋龟": ["loggerhead musk turtle", "Sternotherus minor"],
    "平背": ["flattened musk turtle", "Sternotherus depressus"],
}

def run(cmd, timeout=120):
    """Run shell command, return stdout or None on failure."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except:
        return None

def check_deps():
    """Check yt-dlp and ffmpeg are installed."""
    if not shutil.which("yt-dlp"):
        print("❌ yt-dlp not found. Install: pip install yt-dlp")
        return False
    if not shutil.which("ffmpeg"):
        print("❌ ffmpeg not found. Install: sudo apt install ffmpeg")
        return False
    
    # Check Pillow + imagehash
    try:
        from PIL import Image
        import imagehash
    except ImportError:
        print("❌ Pillow/imagehash not found. Install: pip install Pillow imagehash")
        return False
    
    return True

def search_youtube(query, max_results=5):
    """Search YouTube for videos matching query."""
    # yt-dlp flat search — way faster than full metadata download
    cmd = f'yt-dlp --flat-playlist --dump-json "ytsearch{max_results}:{query}" 2>/dev/null'
    output = run(cmd, timeout=30)
    if not output:
        return []
    
    videos = []
    for line in output.strip().split("\n"):
        try:
            info = json.loads(line)
            videos.append({
                "id": info.get("id", ""),
                "title": info.get("title", ""),
                "duration": info.get("duration", 0),
                "url": f"https://youtube.com/watch?v={info.get('id', '')}",
            })
        except:
            continue
    
    return videos

def download_video(url, output_dir, max_duration=600):
    """Download video + subtitles. Returns (video_path, subtitle_path)."""
    os.makedirs(output_dir, exist_ok=True)
    fname = os.path.join(output_dir, "%(id)s.%(ext)s")
    vid_id = url.split("v=")[-1].split("&")[0]
    
    # Download video with auto-generated subtitles
    cmd = (
        f'yt-dlp -f "best[height<=720]" '
        f'--max-filesize 200M '
        f'--match-filter "duration < {max_duration}" '
        f'-o "{fname}" '
        f'--write-auto-subs --sub-lang en,zh-Hans,zh '  # 自动字幕：英文+中文
        f'--convert-subs srt '  # 转为 SRT 便于解析
        f'--no-playlist '
        f'--socket-timeout 30 '
        f'"{url}" '
        f'2>&1'
    )
    output = run(cmd, timeout=120)
    
    # Find video file
    video_path = None
    for ext in ['mp4', 'webm', 'mkv']:
        path = os.path.join(output_dir, f"{vid_id}.{ext}")
        if os.path.exists(path):
            video_path = path
            break
    
    # Find subtitle file
    sub_path = None
    for lang in ['en', 'zh-Hans', 'zh']:
        path = os.path.join(output_dir, f"{vid_id}.{lang}.srt")
        if os.path.exists(path):
            sub_path = path
            break
    
    return video_path, sub_path

def extract_frames(video_path, output_dir, prefix="frame"):
    """Extract key frames using ffmpeg scene change detection."""
    os.makedirs(output_dir, exist_ok=True)
    
    fname = os.path.join(output_dir, f"{prefix}_%04d.jpg")
    
    # ffmpeg scene change detection: extract frames at scene cuts + regular intervals
    cmd = (
        f'ffmpeg -i "{video_path}" '
        f'-vf "select=gt(scene\\,{SCENE_THRESHOLD}),scale=640:-1" '
        f'-vsync vfr '
        f'-q:v 3 '
        f'-frames:v {MAX_FRAMES_PER_VIDEO * 2} '
        f'"{fname}" '
        f'-y -loglevel error 2>&1'
    )
    run(cmd, timeout=60)
    
    # Count extracted frames
    frames = sorted(Path(output_dir).glob(f"{prefix}_*.jpg"))
    print(f"    🎬 Extracted {len(frames)} candidate frames")
    return frames

def deduplicate_frames(frames, threshold=DEDUP_THRESHOLD):
    """Remove near-duplicate frames using perceptual hashing."""
    from PIL import Image
    import imagehash
    
    if len(frames) <= 1:
        return frames
    
    # Compute hashes
    frame_hashes = []
    for f in frames:
        try:
            img = Image.open(f)
            h = imagehash.average_hash(img)
            frame_hashes.append((f, h))
        except:
            continue
    
    # Keep only dissimilar frames
    kept = [frame_hashes[0]]
    for frame, h in frame_hashes[1:]:
        # Compare against all kept frames
        if all(abs(h - kh) > threshold for _, kh in kept):
            kept.append((frame, h))
    
    print(f"    🔍 Dedup: {len(frames)} → {len(kept)} unique")
    return [f for f, _ in kept]

def save_to_dataset(frames, species_name):
    """Save deduplicated frames to training dataset directory."""
    species_dir = os.path.join(DATASET, species_name)
    os.makedirs(species_dir, exist_ok=True)
    
    # Get next image index
    existing = list(Path(species_dir).glob("yt_*.jpg"))
    start_idx = len(existing)
    
    saved = 0
    for i, frame in enumerate(frames):
        dest = os.path.join(species_dir, f"yt_{start_idx + i:04d}.jpg")
        if not os.path.exists(dest):
            shutil.copy(frame, dest)
            saved += 1
    
    # Save metadata
    meta = {
        "source": "youtube",
        "date": datetime.now().isoformat(),
        "count": saved,
        "species": species_name,
    }
    with open(os.path.join(species_dir, "yt_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)
    
    print(f"    ✅ Saved {saved} images to {species_dir}")
    return saved

def parse_srt(srt_path):
    """Parse SRT subtitle file to plain text."""
    if not srt_path or not os.path.exists(srt_path):
        return ""
    
    with open(srt_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    
    # Remove SRT timestamps and index numbers
    lines = []
    for line in content.split("\n"):
        line = line.strip()
        # Skip empty lines, index numbers, timestamps
        if not line or line.isdigit() or "-->" in line:
            continue
        # Remove HTML tags
        line = re.sub(r'<[^>]+>', '', line)
        lines.append(line)
    
    return " ".join(lines)

def extract_care_info(text, species_name):
    """Extract potential care information from subtitle text."""
    if not text:
        return {}
    
    care = {
        "species": species_name,
        "source": "youtube_subtitles",
        "mentions": [],
    }
    
    # Temperature mentions
    temp_patterns = [
        r'(\d{2,3})\s*(?:degree|degrees|°|℃|℉|F|C)\b',
        r'temperature\s*(?:of|is|around|about)?\s*(\d{2,3})',
    ]
    temps = []
    for pat in temp_patterns:
        temps.extend(re.findall(pat, text, re.IGNORECASE))
    if temps:
        care["temperature_mentions"] = [int(t) for t in temps[:5]]
    
    # Diet mentions
    diet_keywords = ['feed', 'diet', 'eat', 'food', 'pellet', 'insect', 'worm', 'fish', 
                     'vegetable', 'plant', 'fruit', 'shrimp', 'cricket', 'mealworm',
                     '喂食', '食物', '吃', '饲料', '虫子', '鱼', '虾', '蔬菜']
    for kw in diet_keywords:
        if kw.lower() in text.lower():
            care.setdefault("diet_keywords", []).append(kw)
    
    # Size mentions
    size_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:inch|inches|"|cm|mm)\b', text, re.IGNORECASE)
    if size_match:
        care["size_mention"] = size_match.group(0)
    
    # UVB/Lighting mentions
    if re.search(r'\bUVB?\b', text, re.IGNORECASE):
        care["uvb_mentioned"] = True
    if re.search(r'(?:basking|晒背|晒太阳|日光)', text, re.IGNORECASE):
        care["basking_mentioned"] = True
    
    # Humidity
    humidity_match = re.search(r'humidity\s*(?:of|is|around|about)?\s*(\d{1,3})\s*%?', text, re.IGNORECASE)
    if humidity_match:
        care["humidity_mention"] = humidity_match.group(0)
    
    # Water mentions (aquatic vs terrestrial)
    if any(kw in text.lower() for kw in ['aquatic', '水栖', 'swim', '游泳', 'deep water', '深水']):
        care["habitat_hint"] = "aquatic"
    elif any(kw in text.lower() for kw in ['terrestrial', '陆栖', 'land', 'burrow']):
        care["habitat_hint"] = "terrestrial"
    
    return care

def process_species(species_name, search_queries=None):
    """Full pipeline for one species: video → frames + subtitles."""
    if search_queries is None:
        search_queries = SPECIES_SEARCH.get(species_name, [species_name + " turtle care"])
    
    print(f"\n🐢 [{species_name}] Searching videos...")
    
    # Phase 1: Search + filter
    all_videos = []
    for query in search_queries:
        vids = search_youtube(query)
        all_videos.extend(vids)
        time.sleep(1)  # rate limit
    
    # Remove duplicates by ID
    seen = set()
    unique = []
    for v in all_videos:
        if v["id"] not in seen:
            seen.add(v["id"])
            unique.append(v)
    
    print(f"    Found {len(unique)} unique videos")
    
    if not unique:
        return 0
    
    # Phase 2: Download + Extract + Dedup
    tmp_dir = os.path.join(TMP, species_name.replace(" ", "_"))
    os.makedirs(tmp_dir, exist_ok=True)
    
    total_saved = 0
    videos_processed = 0
    
    for video in unique[:MAX_VIDEOS_PER_SPECIES]:
        if videos_processed >= MAX_VIDEOS_PER_SPECIES:
            break
        
        print(f"    📥 {video['title'][:60]}...")
        
        # Download
        result = download_video(video["url"], tmp_dir)
        if not result or not result[0]:
            print(f"    ⚠️ Download failed, skipping")
            continue
        video_path, sub_path = result
        
        # Parse subtitles for care info
        if sub_path:
            sub_text = parse_srt(sub_path)
            if sub_text:
                care = extract_care_info(sub_text, species_name)
                if any(v for v in care.values() if v):  # has useful data
                    # Save care info alongside species
                    care_dir = os.path.join(DATASET, species_name)
                    os.makedirs(care_dir, exist_ok=True)
                    care_path = os.path.join(care_dir, f"yt_care_{video['id']}.json")
                    with open(care_path, "w") as f:
                        json.dump(care, f, indent=2, ensure_ascii=False)
                    keywords = care.get("diet_keywords", [])
                    temps = care.get("temperature_mentions", [])
                    print(f"    📝 字幕: {temps[:2] if temps else '?'}° | {keywords[:3] if keywords else '?'}")
        
        # Extract frames
        frame_dir = os.path.join(tmp_dir, f"frames_{video['id']}")
        frames = extract_frames(video_path, frame_dir)
        if not frames:
            continue
        
        # Dedup
        unique_frames = deduplicate_frames(frames)
        
        # Save
        saved = save_to_dataset(unique_frames, species_name)
        total_saved += saved
        videos_processed += 1
        
        # Cleanup video to save space
        try:
            os.remove(video_path)
        except:
            pass
    
    return total_saved

def main():
    if not check_deps():
        sys.exit(1)
    
    args = sys.argv[1:]
    
    if not args or args[0] == "--help":
        print("Usage:")
        print("  python3 yt_training_pipeline.py [species_name]")
        print("  python3 yt_training_pipeline.py --list       # list available species")
        print("  python3 yt_training_pipeline.py --top N       # process top N species")
        print("  python3 yt_training_pipeline.py --search 'keyword'")
        print("  python3 yt_training_pipeline.py --all         # all species")
        return
    
    if args[0] == "--list":
        print("Available species:")
        for name, queries in SPECIES_SEARCH.items():
            print(f"  {name}: {queries[0]}")
        return
    
    if args[0] == "--search":
        if len(args) < 2:
            print("Usage: --search 'your query'")
            return
        query = " ".join(args[1:])
        print(f"🔍 Searching: {query}")
        vids = search_youtube(query)
        for v in vids:
            print(f"  [{v['duration']}s] {v['title']}")
            print(f"    {v['url']}")
        return
    
    if args[0] == "--all":
        print(f"🚀 Processing all {len(SPECIES_SEARCH)} species...")
        total = 0
        for name in SPECIES_SEARCH:
            saved = process_species(name)
            total += saved
            print(f"  📊 Running total: {total} images")
        print(f"\n✅ Done. {total} images added across {len(SPECIES_SEARCH)} species.")
        return
    
    if args[0] == "--top":
        n = int(args[1]) if len(args) > 1 else 10
        species_list = list(SPECIES_SEARCH.items())[:n]
        print(f"🚀 Processing top {n} species...")
        total = 0
        for name, _ in species_list:
            saved = process_species(name)
            total += saved
        print(f"\n✅ Done. {total} images added across {n} species.")
        return
    
    # Single species
    name = " ".join(args)
    # Fuzzy match
    for key in SPECIES_SEARCH:
        if key in name or name in key:
            saved = process_species(key)
            print(f"\n✅ {saved} images added for {key}")
            return
    
    # Direct search
    saved = process_species(name, [name + " turtle care", name + " turtle unboxing"])
    print(f"\n✅ {saved} images added for {name}")

if __name__ == "__main__":
    main()
