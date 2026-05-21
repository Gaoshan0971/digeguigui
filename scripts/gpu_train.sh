#!/bin/bash
# ============================================
# 滴个龟龟 GPU 训练一键脚本
# 在 GPU 机器上运行: bash gpu_train.sh
# ============================================
set -e

COS_URL="https://digeguigui-1251012364.cos.ap-guangzhou.myqcloud.com/digeguigui_training_20260521_0500.tar.gz?q-sign-algorithm=sha1&q-ak=AKIDRyLVcafbUUYb8a4Oer050jEWpx41sVw9&q-sign-time=1779326036%3B1779412496&q-key-time=1779326036%3B1779412496&q-header-list=host&q-url-param-list=&q-signature=8aa6e23c6ad489eda6a88c4a0450e04c26fb7d04"

echo "📦 下载训练数据..."
cd /root/digeguigui

# 备份旧数据
if [ -d data/training/bak ]; then
    rm -rf data/training/bak
fi
if [ -d data/training/bili_v1 ] || [ -d data/training/inat_v2 ]; then
    echo "  备份旧数据..."
    mkdir -p data/training/bak
    mv data/training/bili_v1 data/training/bak/ 2>/dev/null || true
    mv data/training/bili_v2 data/training/bak/ 2>/dev/null || true
    mv data/training/inat_v2 data/training/bak/ 2>/dev/null || true
    mv data/training/inat_v3 data/training/bak/ 2>/dev/null || true
fi

# 下载
wget -O /tmp/digeguigui_training.tar.gz "$COS_URL"

echo "📦 解压..."
cd /root/digeguigui
tar xzf /tmp/digeguigui_training.tar.gz
rm /tmp/digeguigui_training.tar.gz

# 确认 GPU
echo "🔍 GPU 状态:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "  ⚠️ 无 GPU"

echo ""
echo "🚀 开始训练 Stage 1 (组分类)..."
python3 scripts/train_two_stage.py --stage 1 --epochs 30 --batch-size 32 --lr 3e-4

echo ""
echo "🚀 开始训练 Stage 2 (各组种分类)..."
for group in 水龟_地图 陆龟 蛋龟 侧颈龟 箱龟_闭壳 鳖 其他; do
    echo "  ▶ Stage 2 - $group"
    python3 scripts/train_two_stage.py --stage 2 --group "$group" --epochs 40 --batch-size 32 --lr 3e-4
done

echo ""
echo "✅ 训练完成！模型在 models/ 目录"
ls -lh models/*.pth 2>/dev/null
