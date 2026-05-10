// appraisals.js — 品相鉴赏 API
const db = require('../db');
const { getUser } = require('../middleware/auth');

function register(app) {

  // GET /api/collections/:id/appraisals — 某藏品的鉴赏记录
  app.get('/api/collections/:id/appraisals', (req, res) => {
    const { page = 1, limit = 20 } = req.query;
    const offset = (page - 1) * limit;

    const list = db.prepare(`
      SELECT a.*, u.nickname, u.avatar_url
      FROM appraisals a
      JOIN users u ON a.user_id = u.user_id
      WHERE a.collection_id = ?
      ORDER BY a.created_at DESC
      LIMIT ? OFFSET ?
    `).all(req.params.id, Number(limit), offset);

    res.json({ ok: true, data: { list, page: Number(page), limit: Number(limit) } });
  });

  // POST /api/appraisals — 提交鉴赏（需登录）
  app.post('/api/appraisals', (req, res) => {
    const user = getUser(req, res);
    if (!user) return;

    const { collection_id, comment = '', shell_score = 0, head_score = 0, color_score = 0, body_score = 0, health_score = 0 } = req.body;
    if (!collection_id) return res.status(400).json({ ok: false, error: '缺少藏品ID' });

    const item = db.prepare('SELECT collection_id FROM collections WHERE collection_id = ?').get(collection_id);
    if (!item) return res.status(404).json({ ok: false, error: '藏品不存在' });

    db.prepare(`
      INSERT INTO appraisals (collection_id, user_id, comment, shell_score, head_score, color_score, body_score, health_score)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(collection_id, user.user_id, comment, shell_score, head_score, color_score, body_score, health_score);

    updateCollectionGrade(collection_id);

    res.json({ ok: true, data: { message: '鉴赏提交成功' } });
  });

  // DELETE /api/appraisals/:id
  app.delete('/api/appraisals/:id', (req, res) => {
    const user = getUser(req, res);
    if (!user) return;

    const appraisal = db.prepare('SELECT * FROM appraisals WHERE appraisal_id = ?').get(req.params.id);
    if (!appraisal) return res.status(404).json({ ok: false, error: '鉴赏记录不存在' });
    if (appraisal.user_id !== user.user_id) return res.status(403).json({ ok: false, error: '无权操作' });

    db.prepare('DELETE FROM appraisals WHERE appraisal_id = ?').run(req.params.id);
    updateCollectionGrade(appraisal.collection_id);
    res.json({ ok: true });
  });
}

function updateCollectionGrade(collectionId) {
  const stats = db.prepare(`
    SELECT
      AVG(NULLIF(shell_score, 0)) as avg_shell,
      AVG(NULLIF(head_score, 0)) as avg_head,
      AVG(NULLIF(color_score, 0)) as avg_color,
      AVG(NULLIF(body_score, 0)) as avg_body,
      AVG(NULLIF(health_score, 0)) as avg_health,
      COUNT(*) as cnt
    FROM appraisals WHERE collection_id = ?
  `).get(collectionId);

  if (stats.cnt === 0) return;

  const avg = (stats.avg_shell + stats.avg_head + stats.avg_color + stats.avg_body + stats.avg_health) / 5;

  let grade = '';
  if (avg >= 9) grade = 'S';
  else if (avg >= 8) grade = 'A+';
  else if (avg >= 7) grade = 'A';
  else if (avg >= 5) grade = 'B';
  else if (avg > 0) grade = 'C';

  db.prepare(`
    UPDATE collections SET
      shell_score = ROUND(COALESCE(?, shell_score)),
      head_score = ROUND(COALESCE(?, head_score)),
      color_score = ROUND(COALESCE(?, color_score)),
      body_score = ROUND(COALESCE(?, body_score)),
      health_score = ROUND(COALESCE(?, health_score)),
      overall_grade = ?
    WHERE collection_id = ?
  `).run(stats.avg_shell, stats.avg_head, stats.avg_color, stats.avg_body, stats.avg_health, grade, collectionId);
}

module.exports = { register };
