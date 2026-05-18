#!/usr/bin/env python3
"""龟类识图推理 — 单模型，直接给结论"""
import sys, json, base64, io, re, torch, torch.nn as nn
from torchvision import transforms, models
from PIL import Image

IMAGE_SIZE = 224
MODEL_PATH = '/home/ubuntu/digeguigui/models/turtle_iden_unified.pth'
FALLBACK_PATH = '/home/ubuntu/digeguigui/models/turtle_iden_bili_v1.pth'  # 新模型未就绪时降级

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])
])

def load_model(path):
    ckpt = torch.load(path, map_location='cpu', weights_only=False)
    species_list = ckpt.get('species_list', [])
    state = ckpt.get('model_state') or ckpt
    if not species_list:
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

def bili_label_to_species_id(label):
    """B站标签: '0057_Sternotherus_carinatus' → (57, 'Sternotherus carinatus')"""
    m = re.match(r'^(\d{4})_(.+)', label)
    if m:
        return int(m.group(1)), m.group(2).replace('_', ' ')
    return None, label

def unified_label_to_species_id(label):
    """统一模型标签: '0068' → (68, '')"""
    try:
        return int(label), ''
    except:
        return None, label

if __name__ == '__main__':
    data = json.loads(sys.stdin.read())
    img_b64 = data.get('image_base64', '')
    if ',' in img_b64:
        img_b64 = img_b64.split(',')[1]
    img_bytes = base64.b64decode(img_b64)
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    tensor = transform(img).unsqueeze(0)
    
    import os
    model_path = MODEL_PATH if os.path.exists(MODEL_PATH) else FALLBACK_PATH
    parse_fn = unified_label_to_species_id if model_path == MODEL_PATH else bili_label_to_species_id
    
    model, species_list = load_model(model_path)
    if not model:
        print(json.dumps({'ok': False, 'error': 'model not available'}))
        sys.exit(1)
    
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
        top_probs, top_indices = torch.topk(probs, min(5, len(species_list)), dim=1)
    
    predictions = []
    for prob, idx in zip(top_probs[0].tolist(), top_indices[0].tolist()):
        label = species_list[idx]
        sid, display = parse_fn(label)
        predictions.append({
            'species_id': sid,
            'label': display or label,
            'confidence': round(prob * 100, 1)
        })
    
    top = predictions[0]
    second = predictions[1] if len(predictions) > 1 else {'confidence': 0}
    is_direct = top['confidence'] >= 70 and (top['confidence'] - second['confidence']) >= 15
    
    print(json.dumps({
        'ok': True,
        'data': {
            'verdict': {
                'species_id': top['species_id'],
                'confidence': top['confidence'],
                'is_direct': is_direct,
            },
            'candidates': predictions[:5],
            'engine': 'unified' if model_path == MODEL_PATH else 'bili_fallback',
        }
    }))
