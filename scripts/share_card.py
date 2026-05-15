#!/usr/bin/env python3
"""share_card.py — 生成微信分享卡片图 (5:4, ≤20KB)"""
import sys, json, base64, io, os, hashlib
from PIL import Image, ImageDraw, ImageFont

W, H = 500, 400  # 5:4
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'www', 'share-cards')
FONT = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
QUALITY = 65

os.makedirs(OUT_DIR, exist_ok=True)


def create_card(image_base64, species_name, confidence=0, engine='',
                difficulty='', family='', title='', subtitle='',
                footer='', brand='滴个龟龟 · 拍照识龟'):
    """生成分享卡片，返回保存路径。title/subtitle/footer 为空时按 identify 模式自动生成。"""

    # — 加载原图 —
    pure = image_base64
    if pure.startswith('data:'):
        pure = pure.split(',', 1)[1]
    img_data = base64.b64decode(pure)
    turtle_img = Image.open(io.BytesIO(img_data)).convert('RGB')

    # — 创建画布 —
    canvas = Image.new('RGB', (W, H), '#1a3a2a')

    # — 缩放龟图到上方区域 (W x 260) —
    img_h = 260
    turtle_img = crop_center(turtle_img, W / img_h)
    turtle_img = turtle_img.resize((W, img_h), Image.LANCZOS)
    canvas.paste(turtle_img, (0, 0))

    # — 底部信息区 (140px高) —
    overlay = Image.new('RGBA', (W, 140), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    for y in range(140):
        alpha = int(180 + 60 * (y / 140))
        draw_overlay.rectangle([(0, y), (W, y + 1)], fill=(13, 37, 24, alpha))
    canvas.paste(overlay, (0, H - 140), overlay)

    # — 文字 —
    draw = ImageDraw.Draw(canvas)
    try:
        font_name = ImageFont.truetype(FONT, 28)
        font_sub = ImageFont.truetype(FONT, 14)
        font_tag = ImageFont.truetype(FONT, 11)
    except Exception:
        font_name = ImageFont.load_default()
        font_sub = font_name
        font_tag = font_name

    # 顶部装饰线
    draw.rectangle([(20, H - 140), (W - 20, H - 138)], fill='#d4a853')

    name_y = H - 130

    if title or subtitle:
        # — provenance / 自定义模式 —
        display_title = title or species_name
        draw.text((24, name_y), display_title, fill='#d4a853', font=font_name)

        sub_text = subtitle or '你们能给打几分？'
        draw.text((24, name_y + 34), sub_text, fill='#e8e0c8', font=font_sub)

        if footer:
            draw.text((24, name_y + 60), footer, fill='#6a9a7a', font=font_tag)

        if brand:
            bbox = draw.textbbox((0, 0), brand, font=font_tag)
            bw = bbox[2] - bbox[0]
            draw.text((W - bw - 20, H - 28), brand, fill='#4a7a5a', font=font_tag)
    else:
        # — identify 模式（兼容旧调用）—
        draw.text((24, name_y), species_name, fill='#d4a853', font=font_name)
        badge_text = f'{confidence:.0f}% 置信度 · {engine}'
        draw.text((24, name_y + 34), badge_text, fill='#8ab89a', font=font_sub)

        extra_y = name_y + 58
        extras = []
        if difficulty:
            extras.append(f'饲养难度: {difficulty}')
        if family:
            extras.append(f'科属: {family}')
        if extras:
            draw.text((24, extra_y), ' · '.join(extras), fill='#6a9a7a', font=font_tag)

        bbox = draw.textbbox((0, 0), brand, font=font_tag)
        bw = bbox[2] - bbox[0]
        draw.text((W - bw - 20, H - 28), brand, fill='#4a7a5a', font=font_tag)

    # — 保存 —
    raw = f'{title or species_name}{confidence}{image_base64[:64]}'
    name_hash = hashlib.md5(raw.encode()).hexdigest()[:12]
    filename = f'{name_hash}.jpg'
    filepath = os.path.join(OUT_DIR, filename)
    canvas.save(filepath, 'JPEG', quality=QUALITY, optimize=True)

    sz = os.path.getsize(filepath)
    for q in [50, 40, 35]:
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
        filepath = create_card(
            image_base64=data['image_base64'],
            species_name=data.get('species_name', '未知品种'),
            confidence=data.get('confidence', 0),
            engine=data.get('engine', ''),
            difficulty=data.get('difficulty', ''),
            family=data.get('family', ''),
            title=data.get('title', ''),
            subtitle=data.get('subtitle', ''),
            footer=data.get('footer', ''),
            brand=data.get('brand', '滴个龟龟 · 拍照识龟')
        )
        rel = os.path.relpath(filepath, OUT_DIR)
        print(json.dumps({'ok': True, 'url': f'/share-cards/{rel}', 'path': filepath}))
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}))
        sys.exit(1)
