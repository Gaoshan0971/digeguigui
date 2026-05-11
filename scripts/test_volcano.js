// test_volcano.js — 火山豆包视觉对比测试
const fs = require('fs');

const VOLCANO_KEY = '70ecac5b-07d3-4c8a-82ef-83785a74ce46';

const images = [
  { file: '/home/ubuntu/.hermes/image_cache/img_472846b569db.jpg', truth: '日本石龟' },
  { file: '/home/ubuntu/.hermes/image_cache/img_ca694bf92303.jpg', truth: '西非侧颈龟' },
  { file: '/home/ubuntu/.hermes/image_cache/img_3162da1e435b.jpg', truth: '西非侧颈龟' },
];

async function test(img) {
  const buf = fs.readFileSync(img.file);
  const b64 = buf.toString('base64');
  const start = Date.now();
  
  try {
    const resp = await fetch('https://ark.cn-beijing.volces.com/api/v3/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${VOLCANO_KEY}`
      },
      body: JSON.stringify({
        model: 'doubao-1.5-vision-pro-250328',
        messages: [{
          role: 'user',
          content: [
            { type: 'image_url', image_url: { url: `data:image/jpeg;base64,${b64}` } },
            { type: 'text', text: '这只龟是什么品种？只回答中文品种名，不要任何解释。' }
          ]
        }],
        max_tokens: 20
      })
    });
    
    const data = await resp.json();
    const elapsed = ((Date.now() - start)/1000).toFixed(1);
    
    if (resp.ok) {
      const answer = data.choices?.[0]?.message?.content?.trim() || '?';
      const hit = answer.includes(img.truth) ? '✅' : '❌';
      console.log(`  ${hit} 豆包: ${answer} | 实际: ${img.truth} | ${elapsed}s`);
    } else {
      console.log(`  ❌ API错误: ${JSON.stringify(data).slice(0,200)}`);
    }
  } catch(e) {
    console.log(`  ❌ 请求失败: ${e.message}`);
  }
}

(async () => {
  console.log('🔥 火山豆包视觉模型对比测试\n');
  for (const img of images) {
    const name = img.file.split('/').pop();
    console.log(`📸 ${name}`);
    await test(img);
  }
  console.log('\n✅ 完成');
})();
