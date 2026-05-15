#!/usr/bin/env python3
"""龟类识图模型训练 — EfficientNet-B0 迁移学习"""
import os, json, glob, random
from collections import Counter
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image
from tqdm import tqdm

# ── Config ──
DATA_DIR = '/tmp/turtle_dataset'
MODEL_DIR = '/home/ubuntu/digeguigui/models'
BATCH_SIZE = 16
EPOCHS_PHASE1 = 8   # 冻结backbone，只训分类头
EPOCHS_PHASE2 = 12  # 解冻最后几层
LR = 3e-4
IMAGE_SIZE = 224
MIN_SAMPLES = 20

os.makedirs(MODEL_DIR, exist_ok=True)

# ── 收集数据 ──
species_dirs = []
for d in sorted(os.listdir(DATA_DIR)):
    path = os.path.join(DATA_DIR, d)
    if not os.path.isdir(path): continue
    jpgs = glob.glob(os.path.join(path, '*.jpg'))
    if len(jpgs) >= MIN_SAMPLES:
        species_dirs.append((d, jpgs))

# 建标签映射
species_list = sorted(set(d[0] for d in species_dirs))
label_map = {sp: i for i, sp in enumerate(species_list)}
num_classes = len(species_list)

print(f"品类数: {num_classes}")
print(f"总图数: {sum(len(d[1]) for d in species_dirs)}")
print(f"\n品类分布:")
for sp, imgs in species_dirs:
    print(f"  {sp}: {len(imgs)}张")

# ── 划分 train/val ──
random.seed(42)
train_samples, val_samples = [], []

for sp, imgs in species_dirs:
    random.shuffle(imgs)
    split = int(len(imgs) * 0.8)
    for p in imgs[:split]:
        train_samples.append((p, label_map[sp]))
    for p in imgs[split:]:
        val_samples.append((p, label_map[sp]))

print(f"\n训练集: {len(train_samples)} | 验证集: {len(val_samples)}")

# ── Dataset ──
class TurtleDataset(Dataset):
    def __init__(self, samples, transform=None):
        self.samples = samples
        self.transform = transform or transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.ToTensor(),
            transforms.Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])
        ])
    
    def __len__(self): return len(self.samples)
    
    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert('RGB')
        return self.transform(img), label

val_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])
])

train_ds = TurtleDataset(train_samples)
val_ds = TurtleDataset(val_samples, val_transform)
train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=2)
val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=2)

# ── 模型 ──
model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
# 冻结 backbone
for param in model.parameters():
    param.requires_grad = False
# 替换分类头
model.classifier = nn.Sequential(
    nn.Dropout(0.3),
    nn.Linear(1280, 512),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(512, num_classes)
)

device = torch.device('cpu')
model = model.to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.classifier.parameters(), lr=LR)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS_PHASE1)

# ── 训练 Phase 1: 只训分类头 ──
print("\n=== Phase 1: 训练分类头 ===")
best_acc = 0
for epoch in range(EPOCHS_PHASE1):
    model.train()
    total_loss = 0
    for imgs, labels in tqdm(train_loader, desc=f'Epoch {epoch+1}/{EPOCHS_PHASE1}'):
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        loss = criterion(model(imgs), labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    scheduler.step()
    
    # 验证
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for imgs, labels in val_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            preds = model(imgs).argmax(1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    acc = correct / total
    print(f"  Loss: {total_loss/len(train_loader):.4f} | Val Acc: {acc:.3f}")
    if acc > best_acc:
        best_acc = acc
        torch.save(model.state_dict(), f'{MODEL_DIR}/turtle_iden_phase1.pth')

# ── Phase 2: 解冻最后几层微调 ──
print(f"\n=== Phase 2: 微调 backbone 后几层 (best phase1 acc: {best_acc:.3f}) ===")
model.load_state_dict(torch.load(f'{MODEL_DIR}/turtle_iden_phase1.pth'))

# 解冻 features 的最后3个 block
for param in model.features[-3:].parameters():
    param.requires_grad = True

optimizer = optim.Adam([
    {'params': model.features[-3:].parameters(), 'lr': LR/10},
    {'params': model.classifier.parameters(), 'lr': LR}
])
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS_PHASE2)

best_acc2 = 0
for epoch in range(EPOCHS_PHASE2):
    model.train()
    total_loss = 0
    for imgs, labels in tqdm(train_loader, desc=f'Epoch {epoch+1}/{EPOCHS_PHASE2}'):
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        loss = criterion(model(imgs), labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    scheduler.step()
    
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for imgs, labels in val_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            preds = model(imgs).argmax(1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    acc = correct / total
    print(f"  Loss: {total_loss/len(train_loader):.4f} | Val Acc: {acc:.3f}")
    if acc > best_acc2:
        best_acc2 = acc
        torch.save(model.state_dict(), f'{MODEL_DIR}/turtle_iden_best.pth')

# ── 保存最终模型 ──
torch.save({
    'model_state': model.state_dict(),
    'label_map': label_map,
    'species_list': species_list,
    'num_classes': num_classes,
    'image_size': IMAGE_SIZE,
    'val_acc': best_acc2
}, f'{MODEL_DIR}/turtle_iden_full.pth')

print(f"\n✅ 训练完成！")
print(f"   Phase1 best acc: {best_acc:.3f}")
print(f"   Phase2 best acc: {best_acc2:.3f}")
print(f"   模型保存: {MODEL_DIR}/turtle_iden_full.pth")
print(f"   品类数: {num_classes}")
