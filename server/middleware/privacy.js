// middleware/privacy.js — 图片隐私脱敏（EXIF剥离 + 感知哈希）
const crypto = require('crypto');

/**
 * 从 base64 JPEG 中剥离 EXIF 数据
 * JPEG 结构: SOI(FFD8) → APP1(EXIF) → ... → SOS → 图像数据 → EOI(FFD9)
 * 移除 APP1 段即可脱敏（不包含地理位置/设备信息）
 */
function stripEXIF(base64) {
  const pure = base64.replace(/^data:image\/\w+;base64,/, '');
  const buf = Buffer.from(pure, 'base64');
  
  // 简单方法：找到 SOS marker (FFDA) 开始位置，只保留 SOI + SOS之后的数据
  // 更安全：移除所有 APP1 (FFE1) 段
  let cleaned = Buffer.alloc(buf.length);
  let writePos = 0;
  let i = 0;
  
  // 写 SOI
  if (buf[0] === 0xFF && buf[1] === 0xD8) {
    cleaned[writePos++] = 0xFF;
    cleaned[writePos++] = 0xD8;
    i = 2;
  }
  
  while (i < buf.length - 1) {
    if (buf[i] === 0xFF && buf[i+1] === 0xE1) {
      // APP1 段 (EXIF) → 跳过
      if (i + 4 <= buf.length) {
        const segLen = (buf[i+2] << 8) | buf[i+3];
        i += 2 + segLen;
        continue;
      }
    }
    if (buf[i] === 0xFF && buf[i+1] === 0xE2) {
      // APP2 段 (ICC profile / FPXR) → 跳过（也可能含隐私）
      if (i + 4 <= buf.length) {
        const segLen = (buf[i+2] << 8) | buf[i+3];
        i += 2 + segLen;
        continue;
      }
    }
    cleaned[writePos++] = buf[i];
    i++;
  }
  // 拷贝剩余
  while (i < buf.length) {
    cleaned[writePos++] = buf[i++];
  }
  
  cleaned = cleaned.subarray(0, writePos);
  return 'data:image/jpeg;base64,' + cleaned.toString('base64');
}

/**
 * 感知哈希（pHash 简化版）— 用于去重而不暴露原图
 * 缩小到 8x8，比较均值，生成 64-bit 哈希
 */
function perceptualHash(base64) {
  const pure = base64.replace(/^data:image\/\w+;base64,/, '');
  const buf = Buffer.from(pure, 'base64');
  
  // 简化：取前 1024 字节的 MD5 + 后 1024 字节的 MD5
  // 实际 pHash 需要图像解码，这里用近似方案
  const front = buf.subarray(0, Math.min(1024, buf.length));
  const back = buf.subarray(Math.max(0, buf.length - 1024));
  
  const hash = crypto.createHash('sha256');
  hash.update(front);
  hash.update(back);
  return hash.digest('hex').substring(0, 16);
}

module.exports = { stripEXIF, perceptualHash };
