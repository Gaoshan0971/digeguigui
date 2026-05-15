#!/usr/bin/env python3
"""龟类识图推理服务 — HTTP API 包装"""
import sys, json, base64, io, torch, torch.nn as nn
from torchvision import transforms, models
from PIL import Image

MODEL_PATH = '/home/ubuntu/digeguigui/models/turtle_iden_full.pth'
IMAGE_SIZE = 224

# 加载一次
checkpoint = torch.load(MODEL_PATH, map_location='cpu', weights_only=False)
label_map = checkpoint['label_map']
species_list = checkpoint['species_list']
id_to_sp = {v: k for k, v in label_map.items()}

model = models.efficientnet_b0(weights=None)
model.classifier = nn.Sequential(
    nn.Dropout(0.3), nn.Linear(1280, 512), nn.ReLU(),
    nn.Dropout(0.3), nn.Linear(512, len(species_list))
)
model.load_state_dict(checkpoint['model_state'])
model.eval()

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])
])

def predict(image_bytes):
    """输入图片bytes，返回Top-3预测"""
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    tensor = transform(img).unsqueeze(0)
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
        top_probs, top_indices = torch.topk(probs, 3, dim=1)
    
    results = []
    for prob, idx in zip(top_probs[0].tolist(), top_indices[0].tolist()):
        results.append({
            'species': species_list[idx],
            'confidence': round(prob * 100, 1)
        })
    return results

# HTTP 模式：读stdin的base64图片
if __name__ == '__main__':
    data = json.loads(sys.stdin.read())
    img_b64 = data.get('image_base64', '')
    # 去掉 data:image/xxx;base64, 前缀
    if ',' in img_b64:
        img_b64 = img_b64.split(',')[1]
    img_bytes = base64.b64decode(img_b64)
    results = predict(img_bytes)
    print(json.dumps({'ok': True, 'data': results}))
