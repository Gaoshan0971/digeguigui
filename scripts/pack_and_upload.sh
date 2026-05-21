#!/bin/bash
# 自动打包训练数据 → 上传 COS → 生成 GPU 下载链接
set -e

cd /home/ubuntu/digeguigui
TIMESTAMP=$(date +%Y%m%d_%H%M)
PKG_NAME="digeguigui_training_${TIMESTAMP}.tar.gz"
COS_PATH="$PKG_NAME"
GPU_SCRIPT="scripts/gpu_train.sh"

echo "📦 打包训练数据..."
tar czf "/tmp/$PKG_NAME" \
    data/training/bili_v1 \
    data/training/bili_v2 \
    data/training/inat_v2 \
    data/training/foreign_market \
    data/comment_traits.json \
    scripts/train_two_stage.py \
    scripts/genecalc.py \
    2>/dev/null

SIZE=$(du -h "/tmp/$PKG_NAME" | cut -f1)
echo "   包大小: $SIZE"

echo "☁️ 上传 COS..."
coscmd upload "/tmp/$PKG_NAME" "$COS_PATH"

echo "🔗 生成预签名 URL (24h)..."
URL=$(coscmd signurl "$COS_PATH" --timeout 86400)
echo "   $URL"

# 写 GPU 训练脚本
cat > "/tmp/gpu_train_${TIMESTAMP}.sh" << GPUEOF
#!/bin/bash
# GPU 训练脚本 — 明天开机后运行
set -e
echo "📥 下载数据..."
wget -O /root/digeguigui/training.tar.gz "$URL"
cd /root/digeguigui
echo "📦 解压..."
tar xzf training.tar.gz
echo "🔥 Stage 1: 组分类..."
HF_ENDPOINT=https://hf-mirror.com python3.12 scripts/train_two_stage.py --stage 1 --epochs 30 --batch-size 32
echo "🔥 Stage 2: 种分类..."
for group in 水龟_地图 陆龟 蛋龟 侧颈龟 箱龟_闭壳 鳖 其他; do
    echo "  训练 $group..."
    HF_ENDPOINT=https://hf-mirror.com python3.12 scripts/train_two_stage.py --stage 2 --group "\$group" --epochs 40 --batch-size 32
done
echo "✅ 训练完成！"
echo "📤 拉回模型:"
echo "   scp root@GPU:/root/digeguigui/models/*.pth /home/ubuntu/digeguigui/models/"
echo "   scp root@GPU:/root/digeguigui/models/*.json /home/ubuntu/digeguigui/models/"
GPUEOF

chmod +x "/tmp/gpu_train_${TIMESTAMP}.sh"

echo ""
echo "✅ 完成！"
echo "   COS: $COS_PATH ($SIZE)"
echo "   GPU脚本: /tmp/gpu_train_${TIMESTAMP}.sh"
echo ""
echo "📋 明天操作："
echo "   1. 开机 GPU"
echo "   2. scp /tmp/gpu_train_${TIMESTAMP}.sh root@GPU:/root/"
echo "   3. ssh GPU 'bash gpu_train_${TIMESTAMP}.sh'"
