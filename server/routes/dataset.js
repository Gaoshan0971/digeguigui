// routes/dataset.js — 数据集标注提交 + 审核
const db = require('../db');

// 简单的管理密钥（MVP阶段）
const ADMIN_KEY = 'turtle-admin-2026';

function register(app) {

  // GET /api/dataset/species — 获取所有品种列表（用于下拉选择）
  app.get('/api/dataset/species', (req, res) => {
    const list = db.prepare('SELECT species_id, name_cn, name_latin, family FROM species ORDER BY name_cn').all();
    res.json({ ok: true, data: list });
  });

  // POST /api/dataset/submit — 公开提交标注图片
  app.post('/api/dataset/submit', (req, res) => {
    const { species_name, image_base64, submitter_name = '' } = req.body || {};
    
    if (!species_name) return res.status(400).json({ ok: false, error: '请选择品种' });
    if (!image_base64) return res.status(400).json({ ok: false, error: '请上传图片' });

    // 图片大小限制 5MB base64
    if (image_base64.length > 7 * 1024 * 1024) {
      return res.status(400).json({ ok: false, error: '图片太大，请压缩后上传（最大5MB）' });
    }

    // 匹配品种ID
    let species_id = null;
    const match = db.prepare('SELECT species_id FROM species WHERE name_cn = ?').get(species_name);
    if (match) species_id = match.species_id;

    const result = db.prepare(`
      INSERT INTO dataset_submissions (species_name, species_id, image_base64, submitter_name)
      VALUES (?, ?, ?, ?)
    `).run(species_name, species_id, image_base64, submitter_name);

    res.json({
      ok: true,
      data: {
        submission_id: result.lastInsertRowid,
        message: '提交成功！等待审核。'
      }
    });
  });

  // GET /api/dataset/submissions — 管理端查看提交列表
  app.get('/api/dataset/submissions', (req, res) => {
    const { admin_key = '', status = 'pending', page = 1, limit = 20 } = req.query;
    if (admin_key !== ADMIN_KEY) return res.status(403).json({ ok: false, error: '无权访问' });

    const offset = (Number(page) - 1) * Number(limit);
    const total = db.prepare('SELECT COUNT(*) as cnt FROM dataset_submissions WHERE status = ?').get(status).cnt;
    
    const list = db.prepare(`
      SELECT submission_id, species_name, species_id, submitter_name, status, 
             reviewer_notes, reviewed_at, created_at,
             LENGTH(image_base64) as image_size
      FROM dataset_submissions
      WHERE status = ?
      ORDER BY created_at DESC
      LIMIT ? OFFSET ?
    `).all(status, Number(limit), offset);

    res.json({ ok: true, data: { list, total, page: Number(page), limit: Number(limit) } });
  });

  // GET /api/dataset/submissions/:id/image — 查看提交的图片
  app.get('/api/dataset/submissions/:id/image', (req, res) => {
    const { admin_key = '' } = req.query;
    if (admin_key !== ADMIN_KEY) return res.status(403).json({ ok: false, error: '无权访问' });

    const sub = db.prepare('SELECT image_base64, species_name FROM dataset_submissions WHERE submission_id = ?').get(req.params.id);
    if (!sub) return res.status(404).json({ ok: false, error: '不存在' });

    res.json({ ok: true, data: { image_base64: sub.image_base64, species_name: sub.species_name } });
  });

  // POST /api/dataset/submissions/:id/review — 审核（通过/拒绝）
  app.post('/api/dataset/submissions/:id/review', (req, res) => {
    const { admin_key = '', action, notes = '' } = req.body || {};
    if (admin_key !== ADMIN_KEY) return res.status(403).json({ ok: false, error: '无权访问' });
    if (!['approved', 'rejected'].includes(action)) return res.status(400).json({ ok: false, error: 'action 必须是 approved 或 rejected' });

    const sub = db.prepare('SELECT * FROM dataset_submissions WHERE submission_id = ?').get(req.params.id);
    if (!sub) return res.status(404).json({ ok: false, error: '提交不存在' });

    db.prepare(`
      UPDATE dataset_submissions SET status = ?, reviewer_notes = ?, reviewed_at = datetime('now','localtime')
      WHERE submission_id = ?
    `).run(action, notes, req.params.id);

    res.json({ ok: true, data: { submission_id: Number(req.params.id), status: action } });
  });

  // GET /api/dataset/stats — 统计概览（管理端）
  app.get('/api/dataset/stats', (req, res) => {
    const { admin_key = '' } = req.query;
    if (admin_key !== ADMIN_KEY) return res.status(403).json({ ok: false, error: '无权访问' });

    const stats = db.prepare(`
      SELECT status, COUNT(*) as cnt FROM dataset_submissions GROUP BY status
    `).all();
    
    const bySpecies = db.prepare(`
      SELECT species_name, COUNT(*) as cnt 
      FROM dataset_submissions 
      WHERE status = 'approved'
      GROUP BY species_name 
      ORDER BY cnt DESC
    `).all();

    res.json({ ok: true, data: { stats, by_species: bySpecies } });
  });
}

module.exports = { register };
