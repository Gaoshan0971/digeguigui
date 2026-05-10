// routes/identify.js — AI 拍照识龟
const db = require('../db');

function register(app) {

  // POST /api/identify — AI 识别龟种
  app.post('/api/identify', async (req, res) => {
    const { image_base64 } = req.body || {};
    if (!image_base64) return res.status(400).json({ ok: false, error: '请上传图片' });

    try {
      // 调用 DeepSeek Vision API
      const result = await callDeepSeekVision(image_base64);
      // 匹配本地品种数据
      const enriched = await enrichWithSpeciesDB(result);
      res.json({ ok: true, data: enriched });
    } catch (e) {
      console.error('AI识别失败:', e.message);
      res.status(500).json({ ok: false, error: '识别服务暂时不可用，请稍后重试' });
    }
  });
}

// ========== DeepSeek Vision API ==========

const DEEPSEEK_KEY = 'sk-aa7b869018b640fca4be1c445a298393';

async function callDeepSeekVision(base64Image) {
  // 去掉 data:image/...;base64, 前缀
  const pureBase64 = base64Image.replace(/^data:image\/\w+;base64,/, '');

  const prompt = `你是一个龟类识别专家。请识别这张图片中的龟是什么品种。

请严格按以下 JSON 格式返回（不要包含 markdown 代码块标记）：
{
  "top_species": "中文名",
  "latin_name": "拉丁学名",
  "confidence": 85,
  "characteristics": ["特征1", "特征2", "特征3"],
  "alternatives": [
    {"name": "备选品种1", "latin": "拉丁学名1", "confidence": 10},
    {"name": "备选品种2", "latin": "拉丁学名2", "confidence": 5}
  ]
}

如果图片中不是龟或无法识别，top_species 返回 "无法识别"，confidence 返回 0。

目前数据库中有这些龟种可供参考：黄缘闭壳龟、草龟、果核蛋龟、缅甸陆龟、豹纹陆龟、苏卡达陆龟、猪鼻龟、钻纹龟、巴西龟、鳄龟、金钱龟、鹰嘴龟、安布闭壳龟、黄喉拟水龟、花龟。如果是其他品种也请正常识别。`;

  const resp = await fetch('https://api.deepseek.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${DEEPSEEK_KEY}`
    },
    body: JSON.stringify({
      model: 'deepseek-chat',
      messages: [{
        role: 'user',
        content: [
          { type: 'image_url', image_url: { url: `data:image/jpeg;base64,${pureBase64}` } },
          { type: 'text', text: prompt }
        ]
      }],
      max_tokens: 800,
      temperature: 0.1
    })
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`DeepSeek API error ${resp.status}: ${err}`);
  }

  const data = await resp.json();
  const content = data.choices?.[0]?.message?.content || '';

  // 解析返回的 JSON
  let parsed;
  try {
    // 处理可能的 markdown 代码块
    const clean = content.replace(/```json\s*/g, '').replace(/```\s*/g, '').trim();
    parsed = JSON.parse(clean);
  } catch {
    // 尝试从文本中提取
    parsed = { top_species: '无法识别', latin_name: '', confidence: 0, alternatives: [] };
  }

  return parsed;
}

// ========== 匹配本地品种数据库 ==========

async function enrichWithSpeciesDB(aiResult) {
  const result = {
    candidates: [],
    species: null
  };

  // 收集所有候选
  const candidates = [];

  if (aiResult.top_species && aiResult.top_species !== '无法识别') {
    candidates.push({
      name_cn: aiResult.top_species,
      name_latin: aiResult.latin_name || '',
      confidence: aiResult.confidence || 0,
      characteristics: aiResult.characteristics || []
    });
  }

  if (aiResult.alternatives) {
    for (const alt of aiResult.alternatives) {
      candidates.push({
        name_cn: alt.name,
        name_latin: alt.latin || '',
        confidence: alt.confidence || 0
      });
    }
  }

  // 尝试在数据库中匹配
  for (const cand of candidates) {
    // 模糊匹配品种名
    const species = db.prepare(`
      SELECT * FROM species
      WHERE name_cn LIKE ? OR name_cn LIKE ?
      LIMIT 1
    `).get(`%${cand.name_cn}%`, `%${cand.name_cn.replace(/龟$/, '')}%`);

    if (species) {
      // 解析 JSON 字段
      try { species.traits = JSON.parse(species.traits); } catch {}
      try { species.care_params = JSON.parse(species.care_params); } catch {}

      if (!result.species) {
        // 第一个匹配的作为主结果
        result.species = { ...species, ai_confidence: cand.confidence };
      }
    }

    result.candidates.push({
      name_cn: cand.name_cn,
      name_latin: cand.name_latin,
      confidence: cand.confidence,
      species_id: species ? species.species_id : null
    });
  }

  return result;
}

module.exports = { register };
