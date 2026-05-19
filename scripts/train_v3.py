#!/usr/bin/env python3
"""
滴个龟龟识图模型训练 v3 — GPU暴力版
- ConvNext-Tiny / EfficientNet-B3, 320px输入
- RandAugment + MixUp + LabelSmoothing
- AMP混合精度, CosineAnnealing
- 数据源: inat_v2 + bili_v1 合并

用法:
  python scripts/train_v3.py                          # 默认配置
  python scripts/train_v3.py --model efficientnet_b3  # 换模型
  python scripts/train_v3.py --epochs 50 --lr 1e-3    # 自定义参数
"""
import os, sys, json, glob, random, argparse, time
from pathlib import Path
from collections import Counter
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

# ── Config ──
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIRS = [
    BASE_DIR / 'data' / 'training' / 'inat_v2',
    BASE_DIR / 'data' / 'training' / 'bili_v1',
]
MODEL_DIR = BASE_DIR / 'models'
MODEL_DIR.mkdir(exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument('--model', default='convnext_tiny', choices=[
    'convnext_tiny', 'convnext_small', 'efficientnet_b3', 'efficientnet_b4',
    'swin_tiny', 'vit_base_patch16_224', 'resnet50'
])
parser.add_argument('--image-size', type=int, default=320)
parser.add_argument('--batch-size', type=int, default=32)
parser.add_argument('--epochs', type=int, default=40)
parser.add_argument('--lr', type=float, default=3e-4)
parser.add_argument('--min-samples', type=int, default=30, help='最少图数才纳入训练')
parser.add_argument('--num-workers', type=int, default=4)
parser.add_argument('--amp', action='store_true', default=True, help='混合精度')
parser.add_argument('--no-amp', dest='amp', action='store_false')
parser.add_argument('--output', default='turtle_iden_v3.pth')
args = parser.parse_args()

IMAGE_SIZE = args.image_size
BATCH_SIZE = args.batch_size
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"🚀 设备: {device} | 模型: {args.model} | 分辨率: {IMAGE_SIZE} | Batch: {BATCH_SIZE}")

# ── 收集数据（多数据源合并）──
species_images = {}  # {species_name: [path, ...]}

for data_dir in DATA_DIRS:
    if not data_dir.exists():
        continue
    print(f"📂 扫描: {data_dir}")
    for d in sorted(data_dir.iterdir()):
        if not d.is_dir() or d.name.startswith('.'):
            continue
        jpgs = list(d.glob('*.jpg')) + list(d.glob('*.jpeg')) + list(d.glob('*.png'))
        # 用 species_id（前4位）合并同名品种的不同数据源
        # 目录名格式: {species_id}_{genus}_{species}[_{author}_{year}]
        parts = d.name.split('_', 1)
        sp_id = parts[0] if parts[0].isdigit() and len(parts[0]) == 4 else d.name
        sp_display = d.name  # 保留完整名用于显示
        
        if sp_id not in species_images:
            species_images[sp_id] = {'images': [], 'display': sp_display}
        species_images[sp_id]['images'].extend([str(p) for p in jpgs])
    
# 筛选：只保留图片数足够的品种
species_images = {
    k: v for k, v in species_images.items() 
    if len(v['images']) >= args.min_samples
}

# 排序建标签
species_list = sorted(species_images.keys())
label_map = {sp: i for i, sp in enumerate(species_list)}
num_classes = len(species_list)

total = sum(len(v['images']) for v in species_images.values())
print(f"\n📊 品类: {num_classes} | 总图: {total} | 最少: {min(len(v['images']) for v in species_images.values())} | 最多: {max(len(v['images']) for v in species_images.values())}")
if num_classes < 10:
    print("❌ 品种太少！检查数据目录")
    sys.exit(1)

# 打印品类分布（top 20 + bottom 10）
counts = sorted([(sp, len(v['images'])) for sp, v in species_images.items()], key=lambda x: x[1], reverse=True)
print("\n品类分布 TOP 20:")
for sp, n in counts[:20]:
    print(f"  {sp} ({species_images[sp]['display'][:40]}): {n}张")
print(f"  ...")
for sp, n in counts[-10:]:
    print(f"  {sp} ({species_images[sp]['display'][:40]}): {n}张")

# ── 划分 train/val (stratified) ──
random.seed(42)
np.random.seed(42)
train_samples, val_samples = [], []

for sp, v in species_images.items():
    imgs = v['images']
    random.shuffle(imgs)
    split = max(1, int(len(imgs) * 0.85))
    for p in imgs[:split]:
        train_samples.append((p, label_map[sp]))
    for p in imgs[split:]:
        val_samples.append((p, label_map[sp]))

print(f"\n🔀 训练集: {len(train_samples)} | 验证集: {len(val_samples)}")

# ── 增强 ──
# RandAugment via timm
from timm.data.auto_augment import rand_augment_transform
rand_aug = rand_augment_transform(
    config_str='rand-m7-mstd0.5-inc1',  # 7种增强，中等强度
    hparams={'translate_const': 100, 'img_mean': (124, 116, 104)}
)

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

# ── Dataset ──
class TurtleDataset(Dataset):
    def __init__(self, samples, transform=None):
        self.samples = samples
        self.transform = transform
    
    def __len__(self): 
        return len(self.samples)
    
    def __getitem__(self, idx):
        path, label = self.samples[idx]
        try:
            img = Image.open(path).convert('RGB')
        except Exception:
            img = Image.new('RGB', (IMAGE_SIZE, IMAGE_SIZE), (128,128,128))
        if self.transform:
            img = self.transform(img)
        return img, label

train_ds = TurtleDataset(train_samples, train_transform)
val_ds = TurtleDataset(val_samples, val_transform)

# 样本加权（缓解类别不平衡）
class_counts = Counter(l for _, l in train_samples)
sample_weights = [1.0 / class_counts[l] for _, l in train_samples]
sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler, num_workers=args.num_workers, pin_memory=True)
val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=args.num_workers, pin_memory=True)

# ── 模型 ──
print(f"\n🧠 加载 {args.model}...")
model = timm.create_model(args.model, pretrained=True, num_classes=num_classes)
model = model.to(device)

# ── 损失 & 优化器 ──
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.05)
scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2, eta_min=args.lr*0.01)
scaler = GradScaler() if args.amp else None

# ── 训练 ──
best_acc = 0.0
history = []

print(f"\n{'='*60}")
print(f"🏋️ 开始训练 | {args.epochs} epochs | AMP={args.amp} | LabelSmooth=0.1")
print(f"{'='*60}\n")

for epoch in range(args.epochs):
    # Train
    model.train()
    train_loss, train_correct, train_total = 0, 0, 0
    pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{args.epochs} [train]", leave=False)
    
    for imgs, labels in pbar:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        
        if args.amp:
            with autocast():
                outputs = model(imgs)
                loss = criterion(outputs, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
        
        train_loss += loss.item()
        train_correct += (outputs.argmax(1) == labels).sum().item()
        train_total += labels.size(0)
        pbar.set_postfix({'loss': f'{loss.item():.3f}', 'acc': f'{train_correct/train_total:.3f}'})
    
    train_acc = train_correct / train_total
    scheduler.step()
    
    # Val
    model.eval()
    val_loss, val_correct, val_total = 0, 0, 0
    all_preds, all_labels = [], []
    
    with torch.no_grad():
        for imgs, labels in tqdm(val_loader, desc=f"Epoch {epoch+1}/{args.epochs} [val]", leave=False):
            imgs, labels = imgs.to(device), labels.to(device)
            if args.amp:
                with autocast():
                    outputs = model(imgs)
                    loss = criterion(outputs, labels)
            else:
                outputs = model(imgs)
                loss = criterion(outputs, labels)
            
            val_loss += loss.item()
            _, preds = outputs.max(1)
            val_correct += (preds == labels).sum().item()
            val_total += labels.size(0)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())
    
    val_acc = val_correct / val_total
    lr_now = optimizer.param_groups[0]['lr']
    
    print(f"Epoch {epoch+1:3d} | lr {lr_now:.2e} | "
          f"train loss {train_loss/len(train_loader):.4f} acc {train_acc:.4f} | "
          f"val loss {val_loss/len(val_loader):.4f} acc {val_acc:.4f}", 
          end='')
    
    # Top-3 准确率（微调时更实用）
    if epoch % 5 == 0 or val_acc > best_acc:
        top3 = 0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                outputs = model(imgs)
                _, top3_idx = outputs.topk(3, dim=1)
                top3 += (top3_idx == labels.unsqueeze(1)).any(dim=1).sum().item()
        top3_acc = top3 / val_total
        print(f" top3 {top3_acc:.4f}", end='')
    print()
    
    history.append({'epoch': epoch+1, 'train_loss': train_loss/len(train_loader),
                    'train_acc': train_acc, 'val_loss': val_loss/len(val_loader), 'val_acc': val_acc})
    
    # 保存最佳
    if val_acc > best_acc:
        best_acc = val_acc
        save_path = MODEL_DIR / args.output
        torch.save({
            'epoch': epoch + 1,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'val_acc': val_acc,
            'num_classes': num_classes,
            'species_list': species_list,
            'label_map': label_map,
            'config': vars(args),
        }, save_path)
        print(f"  💾 最佳模型 {val_acc:.4f} → {save_path}")

# ── 最终指标 ──
print(f"\n{'='*60}")
print(f"✅ 训练完成")
print(f"   最佳验证准确率: {best_acc:.4f}")
print(f"   品类数: {num_classes}")
print(f"   模型: {MODEL_DIR / args.output}")
print(f"{'='*60}")

# 保存class映射（推理服务用）
import json
map_path = MODEL_DIR / args.output.replace('.pth', '_classes.json')
with open(map_path, 'w') as f:
    json.dump({'species_list': species_list, 'label_map': label_map, 'num_classes': num_classes}, f, ensure_ascii=False)
print(f"   类别映射: {map_path}")
