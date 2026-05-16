// routes/identify.js — AI 拍照识龟（本地模型 + 混元兜底）
const db = require('../db');
const { spawn } = require('child_process');
const path = require('path');

const INFER_SCRIPT = path.join(__dirname, '..', '..', 'scripts', 'turtle_infer.py');
const PYTHON = '/usr/bin/python3';

function register(app) {

  // POST /api/identify — AI 识别龟种
  app.post('/api/identify', async (req, res) => {
    const { image_base64 } = req.body || {};
    if (!image_base64) return res.status(400).json({ ok: false, error: '请上传图片' });

    try {
      // ── 第一步：本地模型推理 ──
      let localResult = null;
      try {
        localResult = await callLocalModel(image_base64);
      } catch (e) {
        console.log('本地模型不可用，降级到混元:', e.message);
      }

      // ── 判断是否够置信 ──
      if (localResult && localResult.length > 0 && localResult[0].confidence >= 50) {
        // 本地模型够准，直接用
        const enriched = await enrichLocalResult(localResult);
        return res.json({
          ok: true,
          data: { ...enriched, engine: 'efficientnet' }
        });
      }

      // ── 降级：混元视觉 ──
      const hunyuanResult = await callHunyuanVision(image_base64);
      const enriched = await enrichWithSpeciesDB(hunyuanResult);
      // 如果本地有结果但不够置信，作为混元的参考
      if (localResult?.[0]) {
        enriched.local_hint = localResult[0].species;
      }
      res.json({
        ok: true,
        data: { ...enriched, engine: 'hunyuan' }
      });

    } catch (e) {
      console.error('AI识别失败:', e.message);
      res.status(500).json({ ok: false, error: '识别服务暂时不可用，请稍后重试' });
    }
  });

  // ───── 反馈闭环 ─────

  // POST /api/identify/feedback — 用户确认/纠错
  app.post('/api/identify/feedback', (req, res) => {
    const {
      image_base64, model_species_id, model_confidence, model_top3,
      engine, feedback_type, user_species_id = null, token = ''
    } = req.body || {};

    if (!image_base64) return res.status(400).json({ ok: false, error: '缺少图片' });
    if (!['confirmed', 'corrected', 'rejected'].includes(feedback_type)) {
      return res.status(400).json({ ok: false, error: 'feedback_type 必须是 confirmed/corrected/rejected' });
    }
    if (feedback_type === 'corrected' && !user_species_id) {
      return res.status(400).json({ ok: false, error: '纠错时需指定正确的品种ID' });
    }

    // 验证 species_id 是否有效（防止 FK 约束炸进程）
    const validSpeciesId = (id) => {
      if (!id) return null;
      const row = db.prepare('SELECT species_id FROM species WHERE species_id = ?').get(id);
      return row ? id : null;
    };

    const finalSpeciesId = feedback_type === 'rejected' ? null
      : feedback_type === 'corrected' ? validSpeciesId(user_species_id) : validSpeciesId(model_species_id);

    try {
      const result = db.prepare(`
        INSERT INTO identify_feedback (user_token, image_base64, model_species_id,
          model_confidence, model_top3, engine, user_species_id, feedback_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `).run(token, image_base64, model_species_id || null, model_confidence || 0,
        JSON.stringify(model_top3 || []), engine || '', finalSpeciesId, feedback_type);

      res.json({ ok: true, data: { feedback_id: result.lastInsertRowid } });
    } catch (e) {
      console.error('反馈写入失败:', e.message);
      res.status(500).json({ ok: false, error: '反馈保存失败' });
    }
  });

  // GET /api/identify/feedback/stats — 管理端统计
  app.get('/api/identify/feedback/stats', (req, res) => {
    const { admin_key = '' } = req.query;
    if (admin_key !== 'turtle-admin-2026') return res.status(403).json({ ok: false, error: '无权访问' });

    const total = db.prepare('SELECT COUNT(*) as cnt FROM identify_feedback').get();
    const byType = db.prepare('SELECT feedback_type, COUNT(*) as cnt FROM identify_feedback GROUP BY feedback_type').all();
    const bySpecies = db.prepare(`
      SELECT s.name_cn, COUNT(*) as cnt FROM identify_feedback f
      JOIN species s ON s.species_id = f.user_species_id
      WHERE f.user_species_id IS NOT NULL
      GROUP BY f.user_species_id ORDER BY cnt DESC LIMIT 30
    `).all();
    const recent = db.prepare(`
      SELECT f.feedback_id, f.feedback_type, s.name_cn, f.model_confidence, f.engine, f.created_at
      FROM identify_feedback f LEFT JOIN species s ON s.species_id = COALESCE(f.user_species_id, f.model_species_id)
      ORDER BY f.created_at DESC LIMIT 50
    `).all();

    res.json({ ok: true, data: { total: total.cnt, by_type: byType, by_species: bySpecies, recent } });
  });

  // GET /api/identify/feedback/export — 导出训练集
  app.get('/api/identify/feedback/export', (req, res) => {
    const { admin_key = '', feedback_type = 'confirmed,corrected', limit = 500 } = req.query;
    if (admin_key !== 'turtle-admin-2026') return res.status(403).json({ ok: false, error: '无权访问' });

    const types = feedback_type.split(',').map(t => t.trim());
    const placeholders = types.map(() => '?').join(',');
    const rows = db.prepare(`
      SELECT f.feedback_id, f.image_base64, s.name_cn, s.species_id, f.feedback_type
      FROM identify_feedback f JOIN species s ON s.species_id = f.user_species_id
      WHERE f.feedback_type IN (${placeholders}) ORDER BY f.created_at DESC LIMIT ?
    `).all(...types, Number(limit));

    res.json({ ok: true, data: { count: rows.length, items: rows } });
  });

  // ───── 分享卡生成 ─────

  const { spawn: spawnSC } = require('child_process');
  const SHARE_CARD_SCRIPT = path.join(__dirname, '..', '..', 'scripts', 'share_card.py');

  // POST /api/identify/share-card — 生成微信分享卡图片
  app.post('/api/identify/share-card', (req, res) => {
    const { image_base64, species_name, confidence, engine, difficulty, family,
            title, subtitle, footer, brand } = req.body || {};
    if (!image_base64) return res.status(400).json({ ok: false, error: '缺少图片' });

    const py = spawnSC(PYTHON, [SHARE_CARD_SCRIPT]);
    let stdout = '', stderr = '';

    py.stdin.write(JSON.stringify({
      image_base64, species_name: species_name || '未知品种',
      confidence: confidence || 0, engine: engine || '',
      difficulty: difficulty || '', family: family || '',
      title: title || '', subtitle: subtitle || '',
      footer: footer || '', brand: brand || '滴个龟龟 · 领证溯源'
    }));
    py.stdin.end();

    py.stdout.on('data', d => stdout += d);
    py.stderr.on('data', d => stderr += d);

    py.on('close', code => {
      if (code !== 0) {
        console.error('分享卡生成失败:', stderr);
        return res.status(500).json({ ok: false, error: '生成失败' });
      }
      try {
        const result = JSON.parse(stdout);
        if (result.ok) {
          res.json({ ok: true, data: { image_url: result.url } });
        } else {
          res.status(500).json({ ok: false, error: result.error });
        }
      } catch {
        res.status(500).json({ ok: false, error: '解析失败' });
      }
    });

    py.on('error', e => {
      res.status(500).json({ ok: false, error: e.message });
    });
  });

  // POST /api/identify/share-card/batch — 批量登记分享卡
  app.post('/api/identify/share-card/batch', (req, res) => {
    const { species_name, batch_count, anchor_ids } = req.body || {};
    if (!species_name || !batch_count || !anchor_ids?.length) {
      return res.status(400).json({ ok: false, error: '缺少参数' });
    }

    const py = spawnSC(PYTHON, [SHARE_CARD_SCRIPT]);
    let stdout = '', stderr = '';

    py.stdin.write(JSON.stringify({
      mode: 'batch', species_name, batch_count, anchor_ids
    }));
    py.stdin.end();

    py.stdout.on('data', d => stdout += d);
    py.stderr.on('data', d => stderr += d);

    py.on('close', code => {
      if (code !== 0) {
        console.error('批量分享卡生成失败:', stderr);
        return res.status(500).json({ ok: false, error: '生成失败' });
      }
      try {
        const result = JSON.parse(stdout);
        if (result.ok) {
          res.json({ ok: true, data: { image_url: result.url } });
        } else {
          res.status(500).json({ ok: false, error: result.error });
        }
      } catch {
        res.status(500).json({ ok: false, error: '解析失败' });
      }
    });

    py.on('error', e => {
      res.status(500).json({ ok: false, error: e.message });
    });
  });
}

// ========== 本地 EfficientNet 模型 ==========

function callLocalModel(base64Image) {
  return new Promise((resolve, reject) => {
    const py = spawn(PYTHON, [INFER_SCRIPT]);
    let stdout = '', stderr = '';

    py.stdin.write(JSON.stringify({ image_base64: base64Image }));
    py.stdin.end();

    py.stdout.on('data', d => stdout += d);
    py.stderr.on('data', d => stderr += d);

    py.on('close', code => {
      if (code !== 0) return reject(new Error(stderr || `exit ${code}`));
      try {
        const result = JSON.parse(stdout);
        resolve(result.data || []);
      } catch {
        reject(new Error('模型返回格式异常'));
      }
    });

    py.on('error', reject);
  });
}

// ========== 本地结果匹配数据库 ==========

async function enrichLocalResult(predictions) {
  const candidates = [];
  let topSpecies = null;

  for (const pred of predictions) {
    // 模糊匹配中文名
    const species = db.prepare(`
      SELECT * FROM species
      WHERE name_cn LIKE ? OR name_latin LIKE ?
      LIMIT 1
    `).get(`%${pred.species}%`, `%${pred.species}%`);

    if (species && !topSpecies) {
      try { species.traits = JSON.parse(species.traits); } catch {}
      try { species.care_params = JSON.parse(species.care_params); } catch {}
      topSpecies = { ...species, ai_confidence: pred.confidence };
    }

    candidates.push({
      name_cn: pred.species,
      confidence: pred.confidence,
      species_id: species ? species.species_id : null
    });
  }

  return { species: topSpecies, candidates };
}

// ========== 腾讯混元视觉 API (兜底) ==========

const HUNYUAN_KEY = 'sk-9W9gW9vKBlRumlofaDl3g104nKh8iTsQVrhzirEx2lo2lGvU';

async function callHunyuanVision(base64Image) {
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

如果图片中不是龟或无法识别，top_species 返回 "无法识别"，confidence 返回 0。`;

  const resp = await fetch('https://api.hunyuan.cloud.tencent.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${HUNYUAN_KEY}`
    },
    body: JSON.stringify({
      model: 'hunyuan-turbos-vision',
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
    throw new Error(`混元 API error ${resp.status}: ${err}`);
  }

  const data = await resp.json();
  const content = data.choices?.[0]?.message?.content || '';

  let parsed;
  try {
    const clean = content.replace(/```json\s*/g, '').replace(/```\s*/g, '').trim();
    parsed = JSON.parse(clean);
  } catch {
    parsed = { top_species: '无法识别', latin_name: '', confidence: 0, alternatives: [] };
  }

  return parsed;
}

// ========== 混元结果匹配数据库 ==========

async function enrichWithSpeciesDB(aiResult) {
  const result = { candidates: [], species: null };
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

  for (const cand of candidates) {
    const species = db.prepare(`
      SELECT * FROM species
      WHERE name_cn LIKE ? OR name_cn LIKE ?
      LIMIT 1
    `).get(`%${cand.name_cn}%`, `%${cand.name_cn.replace(/龟$/, '')}%`);

    if (species) {
      try { species.traits = JSON.parse(species.traits); } catch {}
      try { species.care_params = JSON.parse(species.care_params); } catch {}
      if (!result.species) {
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
