#!/usr/bin/env python3
"""龟类识图推理服务 — HTTP 常驻，模型只加载一次"""
import json, base64, io, re, os, torch, torch.nn as nn
from torchvision import transforms, models
from PIL import Image
from http.server import HTTPServer, BaseHTTPRequestHandler

IMAGE_SIZE = 224
MODELS_DIR = '/home/ubuntu/digeguigui/models'
PORT = 3457

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])
])

class TurtleIdentifier:
    def __init__(self):
        self.model = None
        self.species_list = []
        self.parse_fn = None
        self.engine = 'none'
        self._load()
    
    def _load(self):
        # Try unified model first, fallback to bili
        for path, parse_fn, name in [
            (os.path.join(MODELS_DIR, 'turtle_iden_unified.pth'), self._parse_unified, 'unified'),
            (os.path.join(MODELS_DIR, 'turtle_iden_bili_v1.pth'), self._parse_bili, 'bili'),
        ]:
            if not os.path.exists(path):
                continue
            try:
                ckpt = torch.load(path, map_location='cpu', weights_only=False)
                species_list = ckpt.get('species_list', [])
                state = ckpt.get('model_state', ckpt)
                if not species_list:
                    continue
                
                num_classes = len(species_list)
                m = models.efficientnet_b0(weights=None)
                m.classifier = nn.Sequential(
                    nn.Dropout(0.3), nn.Linear(1280, 512), nn.ReLU(),
                    nn.Dropout(0.3), nn.Linear(512, num_classes)
                )
                m.load_state_dict(state)
                m.eval()
                
                self.model = m
                self.species_list = species_list
                self.parse_fn = parse_fn
                self.engine = name
                print(f'[infer] Loaded {name} model: {num_classes} classes')
                return
            except Exception as e:
                print(f'[infer] Failed to load {name}: {e}')
    
    def _parse_unified(self, label):
        try:
            return int(label), ''
        except:
            return None, label
    
    def _parse_bili(self, label):
        m = re.match(r'^(\d{4})_(.+)', label)
        if m:
            return int(m.group(1)), m.group(2).replace('_', ' ')
        return None, label
    
    def predict(self, image_bytes):
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        tensor = transform(img).unsqueeze(0)
        
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)
            top_probs, top_indices = torch.topk(probs, min(5, len(self.species_list)), dim=1)
        
        predictions = []
        for prob, idx in zip(top_probs[0].tolist(), top_indices[0].tolist()):
            label = self.species_list[idx]
            sid, display = self.parse_fn(label)
            predictions.append({
                'species_id': sid,
                'label': display or label,
                'confidence': round(prob * 100, 1)
            })
        
        top = predictions[0]
        second = predictions[1] if len(predictions) > 1 else {'confidence': 0}
        is_direct = top['confidence'] >= 70 and (top['confidence'] - second['confidence']) >= 15
        
        return {
            'verdict': {
                'species_id': top['species_id'],
                'confidence': top['confidence'],
                'is_direct': is_direct,
            },
            'candidates': predictions[:5],
            'engine': self.engine,
        }

# ── HTTP Server ──
identifier = TurtleIdentifier()

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/predict':
            self.send_response(404)
            self.end_headers()
            return
        
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length))
        img_b64 = body.get('image_base64', '')
        if ',' in img_b64:
            img_b64 = img_b64.split(',')[1]
        
        try:
            img_bytes = base64.b64decode(img_b64)
            result = identifier.predict(img_bytes)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'data': result}).encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'ok': False, 'error': str(e)}).encode())
    
    def log_message(self, format, *args):
        pass  # 安静

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), Handler)
    print(f'[infer] Listening on :{PORT}')
    server.serve_forever()
