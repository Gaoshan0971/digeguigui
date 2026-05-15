// species.js — 品种百科 API
const db = require('../db');

function register(app) {

  // GET /api/species — 品种列表
  app.get('/api/species', (req, res) => {
    const { family, keyword, page = 1, limit = 20 } = req.query;
    const offset = (page - 1) * limit;

    let where = 'WHERE 1=1';
    const params = [];

    if (family) { where += ' AND family = ?'; params.push(family); }
    if (keyword) { where += ' AND (name_cn LIKE ? OR name_latin LIKE ?)'; params.push(`%${keyword}%`, `%${keyword}%`); }

    const total = db.prepare(`SELECT COUNT(*) as cnt FROM species ${where}`).get(...params).cnt;
    const list = db.prepare(`SELECT * FROM species ${where} ORDER BY difficulty ASC, name_cn ASC LIMIT ? OFFSET ?`).all(...params, Number(limit), offset);

    res.json({ ok: true, data: { list, total, page: Number(page), limit: Number(limit) } });
  });

  // GET /api/species/:id — 品种详情，支持 ?lang=en
  app.get('/api/species/:id', (req, res) => {
    const species = db.prepare('SELECT * FROM species WHERE species_id = ?').get(req.params.id);
    if (!species) return res.status(404).json({ ok: false, error: '品种不存在' });

    // JSON 字段
    species.traits = safeJSON(species.traits);
    species.care_params = safeJSON(species.care_params);

    // 双语支持
    if (req.query.lang === 'en' && species.overview_en) {
      species.overview = species.overview_en;
    }

    // 藏品数
    const collectionCount = db.prepare('SELECT COUNT(*) as cnt FROM collections WHERE species_id = ? AND is_showcase = 1').get(species.species_id).cnt;

    res.json({ ok: true, data: { ...species, collection_count: collectionCount } });
  });

  // GET /api/species/:id/collections — 某品种下的藏品
  app.get('/api/species/:id/collections', (req, res) => {
    const { page = 1, limit = 20, sort = 'newest' } = req.query;
    const offset = (page - 1) * limit;

    const orderBy = sort === 'popular' ? 'c.likes DESC' : 'c.created_at DESC';

    const list = db.prepare(`
      SELECT c.*, u.nickname, u.avatar_url
      FROM collections c
      JOIN users u ON c.user_id = u.user_id
      WHERE c.species_id = ? AND c.is_showcase = 1
      ORDER BY ${orderBy}
      LIMIT ? OFFSET ?
    `).all(req.params.id, Number(limit), offset);

    res.json({ ok: true, data: { list, page: Number(page), limit: Number(limit) } });
  });
}

function safeJSON(str) {
  try { return JSON.parse(str); } catch { return str; }
}

module.exports = { register };
