#!/usr/bin/env python3
"""
两阶段识龟推理服务 v2 — 组分类→种分类 + TTA
HTTP :3457, 兼容旧 API
"""
import json, base64, io, os, sys, torch, torch.nn.functional as F
from torchvision import transforms
from PIL import Image
from http.server import HTTPServer, BaseHTTPRequestHandler
import timm

IMAGE_SIZE = 320
MODELS_DIR = '/home/ubuntu/digeguigui/models'
PORT = 3457
device = 'cpu'

# ── 图像预处理 ──
base_tf = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

def load_convnext(path, num_classes):
    ckpt = torch.load(path, map_location='cpu', weights_only=False)
    # 从 checkpoint 取真实的 class 数（不用外面传的）
    actual_classes = ckpt.get('num_classes', num_classes)
    m = timm.create_model('convnext_tiny', pretrained=False, num_classes=actual_classes)
    
    state = ckpt.get('model_state_dict') or ckpt.get('state_dict', ckpt)
    # v2 模型用 TraitModel wrapper → 去掉 backbone./classifier. 前缀，过滤 trait_head
    new_state = {}
    for k, v in state.items():
        if k.startswith('trait_head.'):
            continue  # 推理不需要 trait head
        elif k.startswith('backbone.'):
            new_state[k[9:]] = v
        elif k.startswith('classifier.'):
            new_state['head.fc.' + k[11:]] = v
        else:
            new_state[k] = v
    m.load_state_dict(new_state, strict=False)
    m.eval()
    return m, actual_classes

class TwoStageIdentifier:
    def __init__(self):
        self.group_model = None
        self.group_classes = []
        self.species_models = {}
        self.species_classes = {}
        self._load()

    def _load(self):
        # 组分类器
        gp = os.path.join(MODELS_DIR, 'turtle_group_v1.pth')
        gc = os.path.join(MODELS_DIR, 'turtle_group_v1_classes.json')
        if os.path.exists(gp):
            if os.path.exists(gc):
                self.group_classes = json.loads(open(gc).read())['classes']
            self.group_model, ncls = load_convnext(gp, len(self.group_classes) if self.group_classes else 7)
            if not self.group_classes:
                self.group_classes = [f'group_{i}' for i in range(ncls)]
            print(f'[infer] Group model: {ncls} groups')

        # 种分类器
        for fn in sorted(os.listdir(MODELS_DIR)):
            if not fn.startswith('turtle_') or not fn.endswith('_species_v2.pth'):
                continue
            group_name = fn.replace('turtle_', '').replace('_species_v2.pth', '')
            class_fn = fn.replace('.pth', '_classes.json')
            class_path = os.path.join(MODELS_DIR, class_fn)
            classes = json.loads(open(class_path).read())['classes'] if os.path.exists(class_path) else None
            model, ncls = load_convnext(os.path.join(MODELS_DIR, fn), len(classes) if classes else 10)
            self.species_models[group_name] = model
            if classes:
                self.species_classes[group_name] = classes
            else:
                self.species_classes[group_name] = [f'{group_name}_{i}' for i in range(ncls)]
            print(f'[infer]   {group_name}: {ncls} species')

        n = len(self.species_models)
        total_sp = sum(len(v) for v in self.species_classes.values())
        print(f'[infer] Ready: 1 group + {n} species models, {total_sp} total species')

    def _tta_predict(self, model, img, num_classes):
        """TTA: center crop + horizontal flip → 2 views avg"""
        t = base_tf(img).unsqueeze(0)
        t_flip = transforms.functional.hflip(t)
        batch = torch.cat([t, t_flip], dim=0)

        with torch.no_grad():
            logits = model(batch)
            probs = F.softmax(logits, dim=1)
            return probs.mean(dim=0)

    def predict(self, image_bytes):
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')

        # Stage 1: 组分类
        gp = self._tta_predict(self.group_model, img, len(self.group_classes))
        g_idx = torch.argmax(gp).item()
        group_name = self.group_classes[g_idx]
        group_conf = gp[g_idx].item()

        # Stage 2: 种分类
        if group_name not in self.species_models:
            return self._format_result(group_name, group_conf, None, 0, [])

        sm = self.species_models[group_name]
        sc = self.species_classes[group_name]
        sp = self._tta_predict(sm, img, len(sc))

        top5_val, top5_idx = torch.topk(sp, min(5, len(sc)))
        candidates = []
        for v, i in zip(top5_val.tolist(), top5_idx.tolist()):
            sid_str = sc[i]
            try:
                sid = int(sid_str.lstrip('0') or '0')
            except:
                sid = None
            candidates.append({
                'species_id': sid,
                'label': sid_str,
                'confidence': round(v * 100, 1)
            })

        top = candidates[0]
        second = candidates[1] if len(candidates) > 1 else {'confidence': 0}
        is_direct = top['confidence'] >= 70 and (top['confidence'] - second['confidence']) >= 15

        return {
            'verdict': {
                'species_id': top['species_id'],
                'confidence': top['confidence'],
                'is_direct': is_direct,
                'group': group_name,
                'group_confidence': round(group_conf * 100, 1),
            },
            'candidates': candidates,
            'engine': 'two_stage_v1',
        }

print('[infer] Loading models...')
identifier = TwoStageIdentifier()

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/predict':
            self.send_response(404); self.end_headers(); return

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
        pass

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), Handler)
    print(f'[infer] Listening on :{PORT}')
    server.serve_forever()
