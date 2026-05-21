"""
bio_features.py — 爬宠生物特征提取 + 验证
Phase 1: ResNet50 预训练模型 → 2048-d 特征向量 → 余弦相似度匹配
用法:
  /usr/bin/python3 bio_features.py extract <image_path>       → 特征向量 base64
  /usr/bin/python3 bio_features.py verify <img1> <img2> [阈值] → {match, confidence}
"""
#   python3 scripts/bio_features.py batch <img1> <img2> ...        → 批量提取

import sys
import json
import base64
import hashlib
from io import BytesIO

import torch
import torchvision.transforms as T
from torchvision.models import resnet50, ResNet50_Weights
from PIL import Image
import numpy as np

# ---------- 模型加载 ----------
_model = None

def get_model():
    global _model
    if _model is None:
        _model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V1)
        _model.fc = torch.nn.Identity()  # 去掉分类头，输出 2048-d
        _model.eval()
    return _model

_transform = T.Compose([
    T.Resize((256, 256)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# ---------- 核心函数 ----------
def extract_features(image_path):
    """从图片提取 2048-d 生物特征向量"""
    img = Image.open(image_path).convert('RGB')
    tensor = _transform(img).unsqueeze(0)
    with torch.no_grad():
        features = get_model()(tensor).squeeze().numpy()
    return features.astype(np.float32)

def features_to_hash(features):
    """特征向量 → SHA256 哈希（不可逆，用于安全存储）"""
    raw = features.tobytes()
    return hashlib.sha256(raw).hexdigest()

def features_to_b64(features):
    """特征向量 → base64（可逆，用于相似度计算）"""
    return base64.b64encode(features.tobytes()).decode('ascii')

def b64_to_features(b64_str):
    """base64 → 特征向量"""
    raw = base64.b64decode(b64_str)
    return np.frombuffer(raw, dtype=np.float32)

def cosine_similarity(f1, f2):
    """余弦相似度 [0, 1]"""
    dot = np.dot(f1, f2)
    norm = np.linalg.norm(f1) * np.linalg.norm(f2)
    if norm == 0:
        return 0.0
    return float(dot / norm)

def verify_identity(img1_path, img2_path, threshold=0.92):
    """验证两张图是否为同一只爬宠"""
    f1 = extract_features(img1_path)
    f2 = extract_features(img2_path)
    sim = cosine_similarity(f1, f2)
    return {
        'match': sim >= threshold,
        'confidence': round(sim, 4),
        'threshold': threshold,
        'verdict': 'MATCH' if sim >= threshold else 'MISMATCH',
        'hash1': features_to_hash(f1),
        'hash2': features_to_hash(f2),
        'dim': len(f1)
    }

# ---------- CLI ----------
if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'help'

    if cmd == 'extract':
        path = sys.argv[2]
        feats = extract_features(path)
        result = {
            'hash': features_to_hash(feats),
            'vector_b64': features_to_b64(feats),
            'dim': int(len(feats)),
            'image': path
        }
        print(json.dumps(result, ensure_ascii=False))

    elif cmd == 'verify':
        img1, img2 = sys.argv[2], sys.argv[3]
        threshold = float(sys.argv[4]) if len(sys.argv) > 4 else 0.92
        result = verify_identity(img1, img2, threshold)
        print(json.dumps(result, ensure_ascii=False))

    elif cmd == 'batch':
        paths = sys.argv[2:]
        results = []
        for p in paths:
            feats = extract_features(p)
            results.append({
                'image': p,
                'hash': features_to_hash(feats),
                'vector_b64': features_to_b64(feats),
                'dim': int(len(feats))
            })
        print(json.dumps(results, ensure_ascii=False))

    else:
        print(json.dumps({
            'usage': {
                'extract': 'python3 scripts/bio_features.py extract <image>',
                'verify': 'python3 scripts/bio_features.py verify <img1> <img2> [threshold=0.92]',
                'batch': 'python3 scripts/bio_features.py batch <img1> <img2> ...'
            }
        }, ensure_ascii=False))
