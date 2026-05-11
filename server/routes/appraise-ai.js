// routes/appraise-ai.js — AI 品相鉴赏（付费服务）
const db = require('../db');
const { getUser } = require('../middleware/auth');

const HUNYUAN_KEY = 'sk-9W9gW9vKBlRumlofaDl3g104nKh8iTsQVrhzirEx2lo2lGvU';

function register(app) {

  // POST /api/collections/:id/appraise-ai — AI 品相鉴赏 (¥9.9)
  app.post('/api/collections/:id/appraise-ai', async (req, res) => {
    const user = getUser(req, res);
    if (!user) return;

    const collectionId = req.params.id;
    const collection = db.prepare(`
      SELECT c.*, s.name_cn, s.name_latin 
      FROM collections c JOIN species s ON c.species_id = s.species_id 
      WHERE c.collection_id = ?
    `).get(collectionId);
    if (!collection) return res.status(404).json({ ok: false, error: '藏品不存在' });

    // 检查是否已AI品鉴过
    const existing = db.prepare(
      "SELECT appraisal_id FROM appraisals WHERE collection_id = ? AND user_id = 0"
    ).get(collectionId);
    if (existing) {
      return res.status(400).json({ ok: false, error: '该藏品已通过AI品鉴' });
    }

    // 获取第一张图片用于分析
    let imageUrls;
    try { imageUrls = JSON.parse(collection.image_urls); } catch { imageUrls = []; }
    if (imageUrls.length === 0) {
      return res.status(400).json({ ok: false, error: '藏品没有图片' });
    }

    const imageBase64 = imageUrls[0]; // 第一张图

    try {
      const result = await callHunyuanAppraisal(imageBase64, collection);
      
      // 保存AI品鉴结果 (user_id=0 表示AI)
      const grades = calcGrades(result.scores);
      db.prepare(`
        INSERT INTO appraisals (collection_id, user_id, comment, shell_score, head_score, color_score, body_score, health_score)
        VALUES (?, 0, ?, ?, ?, ?, ?, ?)
      `).run(collectionId, result.comment || '', 
        result.scores.shell, result.scores.head, result.scores.color, 
        result.scores.body, result.scores.health);

      // 更新藏品得分
      db.prepare(`
        UPDATE collections SET 
          shell_score = ?, head_score = ?, color_score = ?, body_score = ?, health_score = ?,
          overall_grade = ?
        WHERE collection_id = ?
      `).run(result.scores.shell, result.scores.head, result.scores.color,
        result.scores.body, result.scores.health, grades.grade, collectionId);

      res.json({
        ok: true,
        data: {
          collection_id: Number(collectionId),
          scores: result.scores,
          grade: grades.grade,
          grade_label: grades.label,
          market_range: result.market_range,
          comment: result.comment,
          highlights: result.highlights || [],
          flags: result.flags || []
        }
      });
    } catch (e) {
      console.error('AI品鉴失败:', e.message);
      res.status(500).json({ ok: false, error: 'AI品鉴服务暂时不可用，请稍后重试' });
    }
  });

  // GET /api/leaderboard — 段位排行
  app.get('/api/leaderboard', (req, res) => {
    const { page = 1, limit = 20, species_id = '', grade = '' } = req.query;
    const offset = (Number(page) - 1) * Number(limit);

    let where = 'WHERE c.is_showcase = 1 AND c.overall_grade != \'\'';
    const params = [];
    if (species_id) { where += ' AND c.species_id = ?'; params.push(species_id); }
    if (grade) { where += ' AND c.overall_grade = ?'; params.push(grade); }

    const orderMap = { S: 0, 'A+': 1, A: 2, B: 3, C: 4 };
    const list = db.prepare(`
      SELECT c.collection_id, c.overall_grade, c.shell_score, c.head_score, c.color_score, c.body_score, c.health_score,
             c.image_urls, c.caption,
             u.nickname, u.avatar_url, u.role,
             s.name_cn as species_name
      FROM collections c
      JOIN users u ON c.user_id = u.user_id
      JOIN species s ON c.species_id = s.species_id
      ${where}
      LIMIT ? OFFSET ?
    `).all(...params, Number(limit), offset);

    // 排序：按品级，同品级按总分
    list.sort((a, b) => {
      const ga = orderMap[a.overall_grade] ?? 5;
      const gb = orderMap[b.overall_grade] ?? 5;
      if (ga !== gb) return ga - gb;
      const totalA = a.shell_score + a.head_score + a.color_score + a.body_score + a.health_score;
      const totalB = b.shell_score + b.head_score + b.color_score + b.body_score + b.health_score;
      return totalB - totalA;
    });

    // 计算排行
    const ranked = list.map((item, i) => ({
      ...item,
      rank: offset + i + 1,
      image_urls: safeJSON(item.image_urls),
      total_score: item.shell_score + item.head_score + item.color_score + item.body_score + item.health_score
    }));

    res.json({ ok: true, data: { list: ranked, page: Number(page), limit: Number(limit) } });
  });

  // GET /api/users/:id/grade — 用户品鉴师等级
  app.get('/api/users/:id/grade', (req, res) => {
    const user = db.prepare('SELECT user_id, nickname, role, appraisal_count, ai_consistency, appraiser_grade FROM users WHERE user_id = ?').get(req.params.id);
    if (!user) return res.status(404).json({ ok: false, error: '用户不存在' });

    const gradeInfo = getAppraiserGrade(user.appraisal_count || 0, user.ai_consistency || 0);
    
    res.json({
      ok: true,
      data: {
        ...user,
        grade: gradeInfo.grade,
        grade_label: gradeInfo.label,
        grade_emoji: gradeInfo.emoji,
        next_grade: gradeInfo.next,
        progress: gradeInfo.progress
      }
    });
  });
}

// ========== AI品鉴核心 ==========

async function callHunyuanAppraisal(imageBase64, collection) {
  const pureBase64 = imageBase64.replace(/^data:image\/\w+;base64,/, '');

  const prompt = `你是一个资深龟类品相鉴定专家，拥有20年实战经验。请对图片中这只${collection.name_cn}（${collection.name_latin}）进行品相鉴定。

请严格按以下JSON格式返回（不要包含markdown代码块）：
{
  "scores": {
    "shell": 8,     // 壳形品相 1-10分，考虑饱满度、对称性、纹路清晰度
    "head": 7,      // 头部品相 1-10分，考虑头型、头纹、色泽
    "color": 9,     // 色泽品相 1-10分，考虑颜色纯正度、光泽度
    "body": 8,      // 体型品相 1-10分，考虑比例协调、四肢状态
    "health": 9     // 健康状态 1-10分，考虑眼神、活跃度、甲壳完整度
  },
  "comment": "背甲高隆饱满，壳纹清晰，色泽纯正。头部比例适中，四肢有力，整体品相优良。",
  "market_range": "1500-2500元",
  "highlights": ["壳形饱满", "色泽纯正"],
  "flags": []
}

评分标准：
- 9-10分：顶级品相，几乎无瑕疵
- 7-8分：优良品相，有明显优点
- 5-6分：中等品相，有可取之处
- 3-4分：品相较差，有明显缺陷
- 1-2分：严重缺陷

market_range：根据品种和品相，给出合理市场价格区间（人民币）。
highlights：品相亮点，1-3个关键词。
flags：品相缺陷或需要注意的问题，如无则为空数组。`;

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
      max_tokens: 600,
      temperature: 0.3
    })
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`混元API error ${resp.status}: ${err}`);
  }

  const data = await resp.json();
  const content = data.choices?.[0]?.message?.content || '';
  
  try {
    const clean = content.replace(/```json\s*/g, '').replace(/```\s*/g, '').trim();
    return JSON.parse(clean);
  } catch {
    throw new Error('AI返回格式异常');
  }
}

// ========== 品级计算 ==========

function calcGrades(scores) {
  const avg = (scores.shell + scores.head + scores.color + scores.body + scores.health) / 5;
  let grade, label;
  if (avg >= 9) { grade = 'S'; label = '极品'; }
  else if (avg >= 8) { grade = 'A+'; label = '上品'; }
  else if (avg >= 7) { grade = 'A'; label = '良品'; }
  else if (avg >= 5) { grade = 'B'; label = '中品'; }
  else { grade = 'C'; label = '普品'; }
  return { grade, label };
}

// ========== 品鉴师等级 ==========

function getAppraiserGrade(count, consistency) {
  // consistency 0-100
  if (count >= 500 && consistency >= 85) return { grade: 5, label: '鉴神师', emoji: '👑', next: null, progress: 100 };
  if (count >= 200 && consistency >= 75) return { grade: 4, label: '鉴钻师', emoji: '💎', next: '鉴神师', progress: Math.min(100, count/500*100) };
  if (count >= 50 && consistency >= 60)  return { grade: 3, label: '鉴金师', emoji: '🥇', next: '鉴钻师', progress: Math.min(100, count/200*100) };
  if (count >= 10) return { grade: 2, label: '鉴银师', emoji: '🥈', next: '鉴金师', progress: Math.min(100, count/50*100) };
  return { grade: 1, label: '鉴铜师', emoji: '🥉', next: '鉴银师', progress: Math.min(100, count/10*100) };
}

function safeJSON(str) {
  try { return JSON.parse(str); } catch { return str; }
}

module.exports = { register };
