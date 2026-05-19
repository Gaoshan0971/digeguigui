#!/usr/bin/env python3
"""
两级分类训练 v1 — 先分圈内组，再分具体种
Stage 1: 7 组分类器（组间差异大，准确率高）
Stage 2: 每组内种分类器（混淆范围小）

数据自动按 species_id 前缀合并多数据源
"""
import os, sys, json, glob, random, argparse, sqlite3
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torch.cuda.amp import GradScaler, autocast
from torchvision import transforms
from PIL import Image
import timm
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'data' / 'digeguigui.db'
MODEL_DIR = BASE_DIR / 'models'
MODEL_DIR.mkdir(exist_ok=True)

# 数据源
DATA_DIRS = [
    BASE_DIR / 'data' / 'training' / 'bili_v1',
    BASE_DIR / 'data' / 'training' / 'inat_v2',
    BASE_DIR / 'data' / 'training' / 'foreign_market',
]

# 圈内分组映射（合并小类）
GROUP_MERGE = {
    '蛋龟': '蛋龟',
    '陆龟': '陆龟',
    '水龟': '水龟_地图',
    '地图龟': '水龟_地图',
    '侧颈龟': '侧颈龟',
    '鳖': '鳖',
    '箱龟': '箱龟_闭壳',
    '闭壳龟': '箱龟_闭壳',
    '海龟': '其他',
    '': '其他',
}

parser = argparse.ArgumentParser()
parser.add_argument('--stage', type=int, default=1, choices=[1, 2], help='1=组分类, 2=种分类')
parser.add_argument('--group', default='all', help='Stage2时指定组名（all=全训）')
parser.add_argument('--model', default='convnext_tiny')
parser.add_argument('--image-size', type=int, default=320)
parser.add_argument('--batch-size', type=int, default=32)
parser.add_argument('--epochs', type=int, default=30)
parser.add_argument('--lr', type=float, default=3e-4)
parser.add_argument('--min-samples', type=int, default=25)
parser.add_argument('--output', default='')
args = parser.parse_args()

IMAGE_SIZE = args.image_size
BATCH_SIZE = args.batch_size
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"🚀 设备: {device} | Stage {args.stage}")

# ── 加载分组映射 ──
conn = sqlite3.connect(DB_PATH)
species_group = {}
for row in conn.execute("SELECT species_id, group_tags FROM species WHERE category='龟'"):
    sp_id = f"{row[0]:04d}"
    raw_tag = row[1] or ''
    species_group[sp_id] = GROUP_MERGE.get(raw_tag, '其他')
conn.close()

groups = sorted(set(species_group.values()))
print(f"分组: {groups}")

# ── 收集数据 ──
sp_data = defaultdict(list)  # {species_id: [img_paths]}

for data_dir in DATA_DIRS:
    if not data_dir.exists():
        continue
    for d in sorted(data_dir.iterdir()):
        if not d.is_dir():
            continue
        sp_id = d.name[:4] if d.name[:4].isdigit() else d.name
        jpgs = list(d.glob('*.jpg')) + list(d.glob('*.jpeg'))
        sp_data[sp_id].extend([str(p) for p in jpgs])

# 筛选
sp_data = {k: v for k, v in sp_data.items() if len(v) >= args.min_samples and k in species_group}

# ── Stage 1: 组分类 ──
if args.stage == 1:
    group_list = sorted(set(species_group[sp] for sp in sp_data))
    group_map = {g: i for i, g in enumerate(group_list)}
    num_classes = len(group_list)
    
    samples = []
    for sp, imgs in sp_data.items():
        g = species_group[sp]
        for p in imgs:
            samples.append((p, group_map[g]))
    
    print(f"\n📊 Stage 1 — 组分类: {num_classes} 组, {len(samples)} 张图")
    for g in group_list:
        n = sum(1 for sp in sp_data if species_group[sp] == g)
        imgs_n = sum(len(sp_data[sp]) for sp in sp_data if species_group[sp] == g)
        print(f"  {g}: {n}种 {imgs_n}张")

# ── Stage 2: 组内种分类 ──
else:
    if args.group != 'all':
        target_sp = {sp: imgs for sp, imgs in sp_data.items() if species_group[sp] == args.group}
    else:
        target_sp = sp_data
    
    sp_list = sorted(target_sp.keys())
    label_map = {sp: i for i, sp in enumerate(sp_list)}
    num_classes = len(sp_list)
    
    samples = []
    for sp, imgs in target_sp.items():
        for p in imgs:
            samples.append((p, label_map[sp]))
    
    print(f"\n📊 Stage 2 — 种分类: {num_classes} 种, {len(samples)} 张图")
    for sp in sp_list:
        print(f"  {sp} ({species_group[sp]}): {len(target_sp[sp])}张")

output_name = args.output or (f'turtle_group_v1.pth' if args.stage == 1 else f'turtle_{args.group}_species_v1.pth')

# ── 划分 train/val ──
random.seed(42)
np.random.seed(42)
random.shuffle(samples)
split = int(len(samples) * 0.85)
train_samples, val_samples = samples[:split], samples[split:]

print(f"\n🔀 训练: {len(train_samples)} | 验证: {len(val_samples)}")

# ── 增强 ──
from timm.data.auto_augment import rand_augment_transform
rand_aug = rand_augment_transform('rand-m7-mstd0.5-inc1', hparams={'translate_const': 100, 'img_mean': (124, 116, 104)})

train_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE + 32, IMAGE_SIZE + 32)),
    transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.7, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(20),
    transforms.ColorJitter(0.3, 0.3, 0.2, 0.1),
    rand_aug,
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

val_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

class TurtleDataset(Dataset):
    def __init__(self, samples, transform=None):
        self.samples = samples
        self.transform = transform
    def __len__(self): return len(self.samples)
    def __getitem__(self, idx):
        path, label = self.samples[idx]
        try:
            img = Image.open(path).convert('RGB')
        except:
            img = Image.new('RGB', (IMAGE_SIZE, IMAGE_SIZE), (128,128,128))
        if self.transform:
            img = self.transform(img)
        return img, label

train_ds = TurtleDataset(train_samples, train_transform)
val_ds = TurtleDataset(val_samples, val_transform)

class_counts = Counter(l for _, l in train_samples)
sample_weights = [1.0 / class_counts[l] for _, l in train_samples]
sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler, num_workers=2, pin_memory=True)
val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=2, pin_memory=True)

# ── 模型 ──
print(f"\n🧠 加载 {args.model}...")
model = timm.create_model(args.model, pretrained=True, num_classes=num_classes)
model = model.to(device)

criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.05)
scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=8, T_mult=2, eta_min=args.lr*0.01)
scaler = GradScaler()

# ── 训练 ──
best_acc = 0.0
print(f"\n{'='*60}")
print(f"🏋️ {args.epochs} epochs | {num_classes} classes | ConvNext-Tiny {IMAGE_SIZE}px")
print(f"{'='*60}\n")

for epoch in range(args.epochs):
    model.train()
    train_loss, train_correct, train_total = 0, 0, 0
    
    for imgs, labels in tqdm(train_loader, desc=f"E{epoch+1}/{args.epochs} train", leave=False):
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        with autocast():
            outputs = model(imgs)
            loss = criterion(outputs, labels)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        
        train_loss += loss.item()
        train_correct += (outputs.argmax(1) == labels).sum().item()
        train_total += labels.size(0)
    
    train_acc = train_correct / train_total
    scheduler.step()
    
    model.eval()
    val_loss, val_correct, val_total = 0, 0, 0
    with torch.no_grad():
        for imgs, labels in val_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            with autocast():
                outputs = model(imgs)
                loss = criterion(outputs, labels)
            val_loss += loss.item()
            val_correct += (outputs.argmax(1) == labels).sum().item()
            val_total += labels.size(0)
    
    val_acc = val_correct / val_total
    print(f"Epoch {epoch+1:3d} | train {train_loss/len(train_loader):.4f} acc {train_acc:.4f} | val {val_loss/len(val_loader):.4f} acc {val_acc:.4f}")
    
    if val_acc > best_acc:
        best_acc = val_acc
        torch.save({
            'epoch': epoch+1, 'model_state_dict': model.state_dict(),
            'val_acc': val_acc, 'num_classes': num_classes,
            'config': vars(args),
        }, MODEL_DIR / output_name)

print(f"\n✅ 最佳验证: {best_acc:.4f} → {MODEL_DIR / output_name}")

# 保存class映射
if args.stage == 1:
    class_info = group_list
else:
    class_info = sp_list
with open(MODEL_DIR / output_name.replace('.pth', '_classes.json'), 'w') as f:
    json.dump({'classes': class_info, 'num_classes': num_classes}, f, ensure_ascii=False)
