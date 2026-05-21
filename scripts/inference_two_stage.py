#!/usr/bin/env python3
"""
两阶段推理引擎 v1 — 先分圈内组，再分具体种
TTA: 5-crop + flip 平均增强
"""
import json, sys, os
from pathlib import Path
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import timm

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / 'models'
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ── 加载模型 ──
def load_model(path, num_classes):
    model = timm.create_model('convnext_tiny', pretrained=False, num_classes=num_classes)
    state = torch.load(path, map_location=device)
    # timm checkpoint wrapper
    if 'model_state_dict' in state:
        state = state['model_state_dict']
    elif 'state_dict' in state:
        state = state['state_dict']
    model.load_state_dict(state, strict=False)
    model.to(device)
    model.eval()
    return model

# 加载组分类器
group_path = MODEL_DIR / 'turtle_group_v1.pth'
group_classes = json.loads((MODEL_DIR / 'turtle_group_v1_classes.json').read_text())['classes']
group_model = load_model(group_path, len(group_classes))

# 加载各组种分类器
species_models = {}
species_classes = {}
for p in sorted(MODEL_DIR.glob('turtle_*_species_v1.pth')):
    name = p.stem.replace('turtle_', '').replace('_species_v1', '')
    # 名字中的中文和特殊字符就是组名
    group_name = name
    class_json = MODEL_DIR / f'turtle_{group_name}_species_v1_classes.json'
    if not class_json.exists():
        continue
    classes = json.loads(class_json.read_text())['classes']
    species_models[group_name] = load_model(p, len(classes))
    species_classes[group_name] = classes

print(f"✅ 推理引擎就绪: 1 组分类器 + {len(species_models)} 种分类器", file=sys.stderr)

# ── 图像预处理 ──
IMAGE_SIZE = 320
base_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

def tta_predict(model, img, num_classes):
    """TTA: 5-crop + flip → 平均"""
    w, h = img.size
    crops = [
        img,                                    # center
        img.crop((0, 0, IMAGE_SIZE, IMAGE_SIZE)),              # top-left
        img.crop((w-IMAGE_SIZE, 0, w, IMAGE_SIZE)),            # top-right
        img.crop((0, h-IMAGE_SIZE, IMAGE_SIZE, h)),            # bottom-left
        img.crop((w-IMAGE_SIZE, h-IMAGE_SIZE, w, h)),          # bottom-right
    ]
    # 水平翻转
    flipped = [c.transpose(Image.FLIP_LEFT_RIGHT) for c in crops]

    all_imgs = crops + flipped  # 10 views
    batch = torch.stack([base_transform(c) for c in all_imgs]).to(device)

    with torch.no_grad():
        logits = model(batch)
        probs = F.softmax(logits, dim=1)
        avg_prob = probs.mean(dim=0)  # 10-view average

    return avg_prob

# ── 推理 ──
def identify(image_path):
    """两级推理 + TTA"""
    img = Image.open(image_path).convert('RGB')

    # Stage 1: 组分类
    group_prob = tta_predict(group_model, img, len(group_classes))
    group_idx = torch.argmax(group_prob).item()
    group_name = group_classes[group_idx]
    group_conf = group_prob[group_idx].item()

    # Stage 2: 组内种分类
    if group_name not in species_models:
        return {
            'group': group_name,
            'group_conf': round(group_conf, 4),
            'species_id': None,
            'species_conf': None,
            'note': f'组"{group_name}"无种分类器'
        }

    sp_model = species_models[group_name]
    sp_classes = species_classes[group_name]
    sp_prob = tta_predict(sp_model, img, len(sp_classes))
    sp_idx = torch.argmax(sp_prob).item()
    sp_id = sp_classes[sp_idx]
    sp_conf = sp_prob[sp_idx].item()

    # Top-K
    top5_val, top5_idx = torch.topk(sp_prob, min(5, len(sp_classes)))
    top5 = [(sp_classes[i], v.item()) for i, v in zip(top5_idx, top5_val)]

    return {
        'group': group_name,
        'group_conf': round(group_conf, 4),
        'species_id': sp_id,
        'species_conf': round(sp_conf, 4),
        'top5': [(sid, round(c, 4)) for sid, c in top5],
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 inference_two_stage.py <图片路径>")
        sys.exit(1)

    result = identify(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
