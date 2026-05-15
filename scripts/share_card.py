#!/usr/bin/env python3
"""share_card.py — 微信分享卡 (5:4, ≤20KB) · 暖白+古铜金设计"""
import sys, json, base64, io, os, hashlib
from PIL import Image, ImageDraw, ImageFont

W, H = 500, 400  # 5:4
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'www', 'share-cards')
FONT = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'

# 新设计系统
BG = '#F7F4EF'          # 暖白底
CARD_BG = '#FFFFFF'     # 卡片白
GOLD = '#B8956A'        # 古铜金
GOLD_LIGHT = '#D4C4A8'  # 浅金
TEXT = '#2C2416'        # 正文
MUTED = '#8C7B6B'        # 次要
GREEN = '#7A9A9A'       # 正面
BORDER = '#EBE5DB'      # 分割线

os.makedirs(OUT_DIR, exist_ok=True)

QUALITY = 65

def load_fonts():
    try:
        return (
            ImageFont.truetype(FONT, 32),   # title
            ImageFont.truetype(FONT, 18),    # subtitle
            ImageFont.truetype(FONT, 14),    # body
            ImageFont.truetype(FONT, 12),    # tag
        )
    except:
        d = ImageFont.load_default()
        return d, d, d, d


def create_card(image_base64, species_name, confidence=0, engine='',
                difficulty='', family='', title='', subtitle='',
                footer='', brand='滴个龟龟 · 领证溯源'):
    font_title, font_sub, font_body, font_tag = load_fonts()

    # — 加载原图 —
    pure = image_base64
    if pure.startswith('data:'):
        pure = pure.split(',', 1)[1]
    img_data = base64.b64decode(pure)
    turtle_img = Image.open(io.BytesIO(img_data)).convert('RGB')

    # — 画布 —
    canvas = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(canvas)

    # — 顶部分割线 —
    draw.rectangle([(0, 0), (W, 3)], fill=GOLD)

    # — 龟图 (上方 260px) —
    img_h = 260
    turtle_img = crop_center(turtle_img, W / img_h)
    turtle_img = turtle_img.resize((W, img_h), Image.LANCZOS)
    canvas.paste(turtle_img, (0, 3))

    # — 底部信息区 (137px) —
    card_y = 263
    # 白色卡片背景
    draw.rectangle([(16, card_y), (W - 16, H - 16)], fill=CARD_BG)
    # 细边框
    draw.rectangle([(16, card_y), (W - 16, H - 16)], outline=BORDER, width=1)

    text_x = 32
    text_y = card_y + 20

    if title:
        # provenance 模式
        draw.text((text_x, text_y), title, fill=TEXT, font=font_title)
        text_y += 38
        if subtitle:
            draw.text((text_x, text_y), subtitle, fill=MUTED, font=font_body)
            text_y += 24
    else:
        # identify 模式
        draw.text((text_x, text_y), species_name, fill=TEXT, font=font_title)
        text_y += 38
        badge = f'{confidence:.0f}% 置信度 · {engine}'
        draw.text((text_x, text_y), badge, fill=GOLD, font=font_body)
        text_y += 22
        extras = []
        if difficulty:
            extras.append(f'难度: {difficulty}')
        if family:
            extras.append(f'{family}')
        if extras:
            draw.text((text_x, text_y), ' · '.join(extras), fill=MUTED, font=font_tag)
            text_y += 18

    if footer:
        draw.text((text_x, text_y), footer, fill=GREEN, font=font_tag)
        text_y += 18

    # 品牌
    bbox = draw.textbbox((0, 0), brand, font=font_tag)
    bw = bbox[2] - bbox[0]
    draw.text((W - bw - 32, H - 30), brand, fill=MUTED, font=font_tag)

    # — 保存 —
    raw = f'{title or species_name}{confidence}{image_base64[:64]}'
    name_hash = hashlib.md5(raw.encode()).hexdigest()[:12]
    filename = f'{name_hash}.jpg'
    filepath = os.path.join(OUT_DIR, filename)
    canvas.save(filepath, 'JPEG', quality=QUALITY, optimize=True)

    sz = os.path.getsize(filepath)
    for q in [50, 40, 35, 30]:
        if sz <= 20480:
            break
        canvas.save(filepath, 'JPEG', quality=q, optimize=True)
        sz = os.path.getsize(filepath)

    return filepath


def create_batch_card(species_name, batch_count, anchor_ids, image_base64=None):
    """批量登记分享卡 — 不用龟图，纯证书风"""
    font_title, font_sub, font_body, font_tag = load_fonts()

    canvas = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(canvas)

    # 顶部金色条
    draw.rectangle([(0, 0), (W, 4)], fill=GOLD)

    # 证书区
    card_margin = 24
    draw.rectangle([(card_margin, 20), (W - card_margin, H - 20)], fill=CARD_BG, outline=BORDER, width=1)

    cx = W // 2
    y = 52

    # 圆章
    seal_r = 32
    draw.ellipse([(cx - seal_r, y), (cx + seal_r, y + seal_r * 2)], outline=GOLD, width=2)
    draw.text((cx - 18, y + 10), '印', fill=GOLD, font=font_title)

    y += 80

    # 标题
    title_text = f'一窝{batch_count}只全部上户口！'
    bbox = draw.textbbox((0, 0), title_text, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw // 2, y), title_text, fill=TEXT, font=font_title)

    y += 44

    # 品种
    sp_text = f'🐢 {species_name}'
    bbox = draw.textbbox((0, 0), sp_text, font=font_sub)
    sw = bbox[2] - bbox[0]
    draw.text((cx - sw // 2, y), sp_text, fill=MUTED, font=font_sub)

    y += 32

    # 锚定号（显示前3个）
    for i, aid in enumerate(anchor_ids[:3]):
        aid_text = f'#{i+1}  {aid}'
        bbox = draw.textbbox((0, 0), aid_text, font=font_body)
        aw = bbox[2] - bbox[0]
        draw.text((cx - aw // 2, y), aid_text, fill=GOLD, font=font_body)
        y += 22

    if len(anchor_ids) > 3:
        more = f'… 等{len(anchor_ids)}个锚定号'
        bbox = draw.textbbox((0, 0), more, font=font_tag)
        mw = bbox[2] - bbox[0]
        draw.text((cx - mw // 2, y), more, fill=MUTED, font=font_tag)

    # 底部品牌
    brand = '滴个龟龟 · 出生锚定 · 哈希链存证'
    bbox = draw.textbbox((0, 0), brand, font=font_tag)
    bw = bbox[2] - bbox[0]
    draw.text((cx - bw // 2, H - 36), brand, fill=GREEN, font=font_tag)

    # 保存
    raw = f'batch{species_name}{batch_count}{str(anchor_ids)[:64]}'
    name_hash = hashlib.md5(raw.encode()).hexdigest()[:12]
    filename = f'batch_{name_hash}.jpg'
    filepath = os.path.join(OUT_DIR, filename)
    canvas.save(filepath, 'JPEG', quality=QUALITY, optimize=True)

    sz = os.path.getsize(filepath)
    for q in [50, 40, 35, 30]:
        if sz <= 20480:
            break
        canvas.save(filepath, 'JPEG', quality=q, optimize=True)
        sz = os.path.getsize(filepath)

    return filepath


def crop_center(img, target_ratio):
    w, h = img.size
    current = w / h
    if current > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        return img.crop((0, top, w, top + new_h))


if __name__ == '__main__':
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        print(json.dumps({'ok': False, 'error': f'JSON parse error: {e}'}))
        sys.exit(1)

    try:
        mode = data.get('mode', 'single')

        if mode == 'batch':
            filepath = create_batch_card(
                species_name=data.get('species_name', '未知品种'),
                batch_count=data.get('batch_count', 0),
                anchor_ids=data.get('anchor_ids', []),
                image_base64=data.get('image_base64')
            )
        else:
            filepath = create_card(
                image_base64=data.get('image_base64', ''),
                species_name=data.get('species_name', '未知品种'),
                confidence=data.get('confidence', 0),
                engine=data.get('engine', ''),
                difficulty=data.get('difficulty', ''),
                family=data.get('family', ''),
                title=data.get('title', ''),
                subtitle=data.get('subtitle', ''),
                footer=data.get('footer', ''),
                brand=data.get('brand', '滴个龟龟 · 领证溯源')
            )

        rel = os.path.relpath(filepath, OUT_DIR)
        print(json.dumps({'ok': True, 'url': f'/share-cards/{rel}', 'path': filepath}))
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}))
        sys.exit(1)
