// breedings.js — 血统记录 API
const db = require('../db');
const { getUser } = require('../middleware/auth');

function register(app) {

  // GET /api/breedings/:id/pedigree — 血统树
  app.get('/api/breedings/:id/pedigree', (req, res) => {
    const breeding = db.prepare(`
      SELECT b.*, u.nickname as breeder_name
      FROM breedings b
      JOIN users u ON b.breeder_id = u.user_id
      WHERE b.breeding_id = ?
    `).get(req.params.id);

    if (!breeding) return res.status(404).json({ ok: false, error: '繁育记录不存在' });

    if (breeding.sire_collection_id) {
      breeding.sire = db.prepare(`
        SELECT c.*, s.name_cn as species_name FROM collections c
        JOIN species s ON c.species_id = s.species_id
        WHERE c.collection_id = ?
      `).get(breeding.sire_collection_id);
    }
    if (breeding.dam_collection_id) {
      breeding.dam = db.prepare(`
        SELECT c.*, s.name_cn as species_name FROM collections c
        JOIN species s ON c.species_id = s.species_id
        WHERE c.collection_id = ?
      `).get(breeding.dam_collection_id);
    }
    breeding.offspring = db.prepare(`
      SELECT o.*, s.name_cn as species_name
      FROM offspring o
      LEFT JOIN collections c ON o.collection_id = c.collection_id
      LEFT JOIN species s ON c.species_id = s.species_id
      WHERE o.breeding_id = ?
    `).all(req.params.id);

    res.json({ ok: true, data: breeding });
  });

  // GET /api/breedings — 繁育记录列表
  app.get('/api/breedings', (req, res) => {
    const { breeder_id, page = 1, limit = 20 } = req.query;
    const offset = (page - 1) * limit;
    const uid = breeder_id;

    if (!uid) return res.status(400).json({ ok: false, error: '请指定 breeder_id' });

    const list = db.prepare(`
      SELECT b.*, u.nickname as breeder_name
      FROM breedings b
      JOIN users u ON b.breeder_id = u.user_id
      WHERE b.breeder_id = ?
      ORDER BY b.created_at DESC
      LIMIT ? OFFSET ?
    `).all(uid, Number(limit), offset);

    res.json({ ok: true, data: { list, page: Number(page), limit: Number(limit) } });
  });

  // POST /api/breedings — 添加繁育配对（需登录）
  app.post('/api/breedings', (req, res) => {
    const user = getUser(req, res);
    if (!user) return;

    const { sire_collection_id, dam_collection_id, pairing_date = '', notes = '' } = req.body;

    const result = db.prepare(`
      INSERT INTO breedings (breeder_id, sire_collection_id, dam_collection_id, pairing_date, notes)
      VALUES (?, ?, ?, ?, ?)
    `).run(user.user_id, sire_collection_id || null, dam_collection_id || null, pairing_date, notes);

    const breeding = db.prepare('SELECT * FROM breedings WHERE breeding_id = ?').get(result.lastInsertRowid);
    res.json({ ok: true, data: breeding });
  });

  // POST /api/breedings/:id/offspring — 添加子代记录（需登录）
  app.post('/api/breedings/:id/offspring', (req, res) => {
    const user = getUser(req, res);
    if (!user) return;

    const breeding = db.prepare('SELECT * FROM breedings WHERE breeding_id = ?').get(req.params.id);
    if (!breeding) return res.status(404).json({ ok: false, error: '繁育记录不存在' });
    if (breeding.breeder_id !== user.user_id) return res.status(403).json({ ok: false, error: '无权操作' });

    const { collection_id, description = '', image_url = '' } = req.body;
    db.prepare(`
      INSERT INTO offspring (breeding_id, collection_id, description, image_url)
      VALUES (?, ?, ?, ?)
    `).run(req.params.id, collection_id || null, description, image_url);

    const cnt = db.prepare('SELECT COUNT(*) as cnt FROM offspring WHERE breeding_id = ?').get(req.params.id).cnt;
    db.prepare('UPDATE breedings SET offspring_count = ? WHERE breeding_id = ?').run(cnt, req.params.id);

    res.json({ ok: true, data: { message: '子代记录已添加' } });
  });

  // GET /api/breeders/:id — 繁育者主页
  app.get('/api/breeders/:id', (req, res) => {
    const user = db.prepare('SELECT user_id, nickname, avatar_url, role, reputation, city, created_at FROM users WHERE user_id = ?').get(req.params.id);
    if (!user) return res.status(404).json({ ok: false, error: '用户不存在' });

    const collections = db.prepare('SELECT COUNT(*) as cnt FROM collections WHERE user_id = ? AND is_showcase = 1').get(req.params.id).cnt;
    const breedings = db.prepare('SELECT COUNT(*) as cnt FROM breedings WHERE breeder_id = ?').get(req.params.id).cnt;
    const offspring = db.prepare('SELECT SUM(offspring_count) as cnt FROM breedings WHERE breeder_id = ?').get(req.params.id).cnt || 0;

    res.json({ ok: true, data: { ...user, collection_count: collections, breeding_count: breedings, offspring_count: offspring } });
  });
}

module.exports = { register };
