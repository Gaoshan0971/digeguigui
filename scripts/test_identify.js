// test_identify.js — AI识龟批量测试 (v2: 匹配混元返回格式)
const fs = require('fs');
const path = require('path');

const images = [
  '/home/ubuntu/.hermes/image_cache/img_472846b569db.jpg',
  '/home/ubuntu/.hermes/image_cache/img_ca694bf92303.jpg',
  '/home/ubuntu/.hermes/image_cache/img_3162da1e435b.jpg',
];

async function testImage(filepath) {
  const basename = path.basename(filepath);
  const buf = fs.readFileSync(filepath);
  const b64 = buf.toString('base64');
  
  console.log(`\n📸 测试: ${basename} (${(buf.length/1024).toFixed(1)}KB)`);
  
  const start = Date.now();
  try {
    const resp = await fetch('http://localhost:3456/api/identify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_base64: b64 }),
    });
    const data = await resp.json();
    const elapsed = ((Date.now() - start) / 1000).toFixed(1);
    
    if (data.ok) {
      const r = data.data;
      console.log(`   耗时: ${elapsed}s`);
      
      if (r.species) {
        const s = r.species;
        console.log(`   🎯 识别: ${s.name_cn} (${s.name_latin})`);
        console.log(`   📊 AI置信度: ${s.ai_confidence}%`);
        console.log(`   🏷️  科: ${s.family} | 难度: ${'⭐'.repeat(s.difficulty)}`);
        if (s.overview) console.log(`   📝 ${s.overview}`);
      }
      
      if (r.candidates && r.candidates.length > 0) {
        console.log(`   📋 候选列表:`);
        r.candidates.forEach((c, i) => {
          const marker = i === 0 ? '→' : ' ';
          const matched = c.species_id ? '✅' : '❓';
          console.log(`     ${marker} ${matched} ${c.name_cn} (${c.confidence}%) ${c.name_latin || ''}`);
        });
      }
      
      if (!r.species && (!r.candidates || r.candidates.length === 0)) {
        console.log(`   ⚠️ 未识别到任何龟种`);
      }
    } else {
      console.log(`   ❌ API错误: ${data.error}`);
    }
  } catch(e) {
    console.log(`   ❌ 请求失败: ${e.message}`);
  }
}

(async () => {
  console.log('🐢 滴个龟龟 AI识龟测试 — 混元视觉引擎\n');
  for (const img of images) {
    if (fs.existsSync(img)) {
      await testImage(img);
    } else {
      console.log(`\n❌ 文件不存在: ${img}`);
    }
  }
  console.log('\n✅ 测试完成！');
})();
