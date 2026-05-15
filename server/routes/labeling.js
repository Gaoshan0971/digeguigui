// routes/labeling.js — 品鉴标注工具 API
const db = require('../db');

function register(app) {

  // GET /api/v2/labeling/queue — 各品种待标注图片数
  app.get('/api/v2/labeling/queue', (req, res) => {
    // 从 dataset_submissions 取未标注的图
    const rows = db.prepare(`
      SELECT d.species_name, d.species_id, s.name_cn, s.name_latin,
             COUNT(*) as total,
             COUNT(CASE WHEN d.status='pending' THEN 1 END) as unlabeled
      FROM dataset_submissions d
      LEFT JOIN species s ON d.species_id = s.species_id
      GROUP BY d.species_name
      HAVING unlabeled > 0
      ORDER BY unlabeled DESC
      LIMIT 50
    `).all();
    res.json({ ok: true, data: rows });
  });

  // GET /api/v2/labeling/next?species_id=X — 取一张待标注图
  app.get('/api/v2/labeling/next', (req, res) => {
    const { species_id } = req.query;
    let row;
    if (species_id) {
      row = db.prepare(`
        SELECT submission_id, species_name, species_id, image_base64, submitter_name
        FROM dataset_submissions
        WHERE species_id = ? AND status = 'pending'
        LIMIT 1
      `).get(species_id);
    } else {
      row = db.prepare(`
        SELECT submission_id, species_name, species_id, image_base64, submitter_name
        FROM dataset_submissions
        WHERE status = 'pending'
        ORDER BY RANDOM() LIMIT 1
      `).get();
    }
    if (!row) return res.status(404).json({ ok: false, error: '无待标注图片' });
    res.json({ ok: true, data: row });
  });

  // POST /api/v2/labeling — 提交标注
  app.post('/api/v2/labeling', (req, res) => {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      try {
        const { submission_id, species_id, image_url, shell, head, color, body, health, grade, market_range, comment } = JSON.parse(body);
        if (!species_id) return res.status(400).json({ ok: false, error: '缺少 species_id' });
        if (!grade) return res.status(400).json({ ok: false, error: '缺少 grade' });

        const scores = [shell, head, color, body, health];
        if (scores.some(s => s < 1 || s > 10)) {
          return res.status(400).json({ ok: false, error: '分数需在 1-10 之间' });
        }

        db.prepare(`
          INSERT INTO labeled_appraisals (species_id, image_url, shell_score, head_score, color_score, body_score, health_score, overall_grade, market_range, comment)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `).run(species_id, image_url || '', shell, head, color, body, health, grade, market_range || '', comment || '');

        // 标记 dataset_submission 为已处理
        if (submission_id) {
          db.prepare(`UPDATE dataset_submissions SET status='labeled', reviewed_at=datetime('now','localtime') WHERE submission_id=?`).run(submission_id);
        }

        res.json({ ok: true, data: { labeled: 1 } });
      } catch (e) {
        res.status(400).json({ ok: false, error: e.message });
      }
    });
  });

  // GET /api/v2/labeling/stats — 标注统计
  app.get('/api/v2/labeling/stats', (req, res) => {
    const total = db.prepare('SELECT COUNT(*) as cnt FROM labeled_appraisals').get();
    const byGrade = db.prepare(`
      SELECT overall_grade, COUNT(*) as cnt FROM labeled_appraisals GROUP BY overall_grade ORDER BY cnt DESC
    `).all();
    const bySpecies = db.prepare(`
      SELECT s.name_cn, COUNT(*) as cnt
      FROM labeled_appraisals l JOIN species s ON l.species_id = s.species_id
      GROUP BY l.species_id ORDER BY cnt DESC LIMIT 10
    `).all();
    res.json({ ok: true, data: { total: total.cnt, byGrade, bySpecies } });
  });

  // GET /api/v2/labeling/export — 导出训练数据 JSON
  app.get('/api/v2/labeling/export', (req, res) => {
    const rows = db.prepare(`
      SELECT l.*, s.name_cn, s.name_latin
      FROM labeled_appraisals l
      JOIN species s ON l.species_id = s.species_id
      ORDER BY l.created_at DESC
    `).all();
    res.json({ ok: true, data: rows, total: rows.length });
  });
}

module.exports = { register };
