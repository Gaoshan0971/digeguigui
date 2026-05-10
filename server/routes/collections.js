// collections.js — 藏品 API
const db = require('../db');
const { getUser } = require('../middleware/auth');

function safeJSON(str) {
  try { return JSON.parse(str); } catch { return str; }
}

function register(app) {

  // GET /api/collections — 展示墙（全平台藏品流）
  app.get('/api/collections', (req, res) => {
    const { species_id, city, page = 1, limit = 20, sort = 'newest' } = req.query;
    const offset = (page - 1) * limit;

    let where = 'WHERE c.is_showcase = 1';
    const params = [];

    if (species_id) { where += ' AND c.species_id = ?'; params.push(species_id); }
    if (city) { where += ' AND c.city LIKE ?'; params.push(`%${city}%`); }

    const orderBy = sort === 'popular' ? 'c.likes DESC' : 'c.created_at DESC';

    const list = db.prepare(`
      SELECT c.*, u.nickname, u.avatar_url, s.name_cn as species_name
      FROM collections c
      JOIN users u ON c.user_id = u.user_id
      JOIN species s ON c.species_id = s.species_id
      ${where}
      ORDER BY ${orderBy}
      LIMIT ? OFFSET ?
    `).all(...params, Number(limit), offset);

    res.json({ ok: true, data: { list, page: Number(page), limit: Number(limit) } });
  });

  // GET /api/collections/:id — 藏品详情
  app.get('/api/collections/:id', (req, res) => {
    const item = db.prepare(`
      SELECT c.*, u.nickname, u.avatar_url, u.user_id, s.name_cn as species_name
      FROM collections c
      JOIN users u ON c.user_id = u.user_id
      JOIN species s ON c.species_id = s.species_id
      WHERE c.collection_id = ?
    `).get(req.params.id);

    if (!item) return res.status(404).json({ ok: false, error: '藏品不存在' });

    item.image_urls = safeJSON(item.image_urls);

    // 鉴赏评论
    const appraisals = db.prepare(`
      SELECT a.*, u.nickname, u.avatar_url
      FROM appraisals a
      JOIN users u ON a.user_id = u.user_id
      WHERE a.collection_id = ?
      ORDER BY a.created_at DESC
      LIMIT 50
    `).all(req.params.id);

    res.json({ ok: true, data: { ...item, appraisals } });
  });

  // POST /api/collections — 上传藏品（需登录）
  app.post('/api/collections', (req, res) => {
    const user = getUser(req, res);
    if (!user) return;

    const { species_id, image_urls = [], caption = '', city = '' } = req.body;
    if (!species_id) return res.status(400).json({ ok: false, error: '请选择品种' });

    const result = db.prepare(`
      INSERT INTO collections (user_id, species_id, image_urls, caption, city, is_showcase)
      VALUES (?, ?, ?, ?, ?, 1)
    `).run(user.user_id, species_id, JSON.stringify(image_urls), caption, city);

    const item = db.prepare('SELECT * FROM collections WHERE collection_id = ?').get(result.lastInsertRowid);
    res.json({ ok: true, data: item });
  });

  // PUT /api/collections/:id — 更新藏品信息
  app.put('/api/collections/:id', (req, res) => {
    const user = getUser(req, res);
    if (!user) return;

    const item = db.prepare('SELECT * FROM collections WHERE collection_id = ?').get(req.params.id);
    if (!item) return res.status(404).json({ ok: false, error: '藏品不存在' });
    if (item.user_id !== user.user_id) return res.status(403).json({ ok: false, error: '无权操作' });

    const { caption, city, is_showcase } = req.body;
    db.prepare('UPDATE collections SET caption = COALESCE(?, caption), city = COALESCE(?, city), is_showcase = COALESCE(?, is_showcase) WHERE collection_id = ?')
      .run(caption ?? null, city ?? null, is_showcase ?? null, req.params.id);

    res.json({ ok: true, data: db.prepare('SELECT * FROM collections WHERE collection_id = ?').get(req.params.id) });
  });

  // DELETE /api/collections/:id
  app.delete('/api/collections/:id', (req, res) => {
    const user = getUser(req, res);
    if (!user) return;

    const item = db.prepare('SELECT * FROM collections WHERE collection_id = ?').get(req.params.id);
    if (!item) return res.status(404).json({ ok: false, error: '藏品不存在' });
    if (item.user_id !== user.user_id) return res.status(403).json({ ok: false, error: '无权操作' });

    db.prepare('DELETE FROM collections WHERE collection_id = ?').run(req.params.id);
    res.json({ ok: true });
  });
}

module.exports = { register };
