#!/usr/bin/env python3
"""龟类识图推理 v2 — 单模型加载，支持双模型 ensemble（当二者都可用时）"""
import sys, json, base64, io, re, os, torch, torch.nn as nn
from torchvision import transforms, models
from PIL import Image

IMAGE_SIZE = 224
MODELS_DIR = '/home/ubuntu/digeguigui/models'

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])
])

def load_model(path):
    ckpt = torch.load(path, map_location='cpu', weights_only=False)
    # 检查是否有 metadata
    if 'species_list' in ckpt and 'model_state' in ckpt:
        species_list = ckpt['species_list']
        state = ckpt['model_state']
    else:
        # 纯 state_dict — 无法确定类别数，回退
        return None, []
    
    num_classes = len(species_list)
    m = models.efficientnet_b0(weights=None)
    m.classifier = nn.Sequential(
        nn.Dropout(0.3), nn.Linear(1280, 512), nn.ReLU(),
        nn.Dropout(0.3), nn.Linear(512, num_classes)
    )
    m.load_state_dict(state)
    m.eval()
    return m, species_list

def predict(model, species_list, tensor):
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
        top_probs, top_indices = torch.topk(probs, min(5, len(species_list)), dim=1)
    
    results = []
    for prob, idx in zip(top_probs[0].tolist(), top_indices[0].tolist()):
        results.append({
            'species': species_list[idx],
            'confidence': round(prob * 100, 1)
        })
    return results

def bili_label_to_species_id(label):
    m = re.match(r'^(\d{4})_(.+)', label)
    if m:
        return int(m.group(1)), m.group(2).replace('_', ' ')
    return None, label

def parse_old_label(label):
    """旧模型标签是中文名，直接返回"""
    return None, label

def merge_predictions(all_preds, parse_fn, source_name):
    """将模型输出转换成统一格式"""
    results = []
    for p in all_preds:
        sid, display_name = parse_fn(p['species'])
        results.append({
            'source': source_name,
            'species_label': display_name,
            'species_id': sid,
            'confidence': p['confidence']
        })
    return results

if __name__ == '__main__':
    data = json.loads(sys.stdin.read())
    img_b64 = data.get('image_base64', '')
    if ',' in img_b64:
        img_b64 = img_b64.split(',')[1]
    img_bytes = base64.b64decode(img_b64)
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    tensor = transform(img).unsqueeze(0)
    
    all_results = []
    engines = {}
    
    # 加载 B站模型
    bili_path = os.path.join(MODELS_DIR, 'turtle_iden_bili_v1.pth')
    if os.path.exists(bili_path):
        try:
            bili_model, bili_species = load_model(bili_path)
            if bili_model:
                bili_preds = predict(bili_model, bili_species, tensor)
                all_results.extend(merge_predictions(bili_preds, bili_label_to_species_id, 'bili'))
                engines['bili'] = True
        except Exception as e:
            engines['bili'] = False
    else:
        engines['bili'] = False
    
    # 加载旧模型
    old_path = os.path.join(MODELS_DIR, 'turtle_iden_full.pth')
    if os.path.exists(old_path):
        try:
            old_model, old_species = load_model(old_path)
            if old_model:
                old_preds = predict(old_model, old_species, tensor)
                all_results.extend(merge_predictions(old_preds, parse_old_label, 'old'))
                engines['old'] = True
        except Exception as e:
            engines['old'] = False
    else:
        engines['old'] = False
    
    # 按置信度排序
    all_results.sort(key=lambda x: x['confidence'], reverse=True)
    
    # 判定
    is_direct = False
    if len(all_results) >= 1:
        c1 = all_results[0]['confidence']
        c2 = all_results[1]['confidence'] if len(all_results) > 1 else 0
        is_direct = (c1 >= 70) and (c1 - c2 >= 15)
    
    print(json.dumps({
        'ok': True,
        'data': {
            'predictions': all_results[:5],
            'verdict': {
                'is_direct': is_direct,
                'top_confidence': all_results[0]['confidence'] if all_results else 0,
                'gap': round(all_results[0]['confidence'] - (all_results[1]['confidence'] if len(all_results)>1 else 0), 1) if all_results else 0,
            },
            'engines': engines,
        }
    }))
