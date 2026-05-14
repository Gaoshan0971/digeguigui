// routes/morphs.js — 品系/基因 API
module.exports.register = function (app) {
  const db = require('../db');

  // GET /api/v2/stats — 数据库统计
  app.get('/api/v2/stats', (req, res) => {
    const species = db.prepare('SELECT category, COUNT(*) as cnt FROM species GROUP BY category ORDER BY cnt DESC').all();
    const total = db.prepare('SELECT COUNT(*) as cnt FROM species').get().cnt;
    const families = db.prepare("SELECT COUNT(DISTINCT family) as cnt FROM species WHERE family != ''").get().cnt;
    const genes = db.prepare('SELECT COUNT(*) as cnt FROM morph_genes').get().cnt;
    const combos = db.prepare('SELECT COUNT(*) as cnt FROM morph_combinations').get().cnt;
    res.json({ ok: true, data: { total, families, genes, combos, categories: species } });
  });

  // GET /api/v2/species — 搜索/过滤物种（支持 category, q, limit, offset）
  app.get('/api/v2/species', (req, res) => {
    const q = req.query || {};
    let sql = 'SELECT * FROM species WHERE 1=1';
    const params = [];
    if (q.category) { sql += ' AND category = ?'; params.push(q.category); }
    if (q.q) { sql += ' AND (name_cn LIKE ? OR name_latin LIKE ? OR common_name_en LIKE ?)'; params.push(`%${q.q}%`, `%${q.q}%`, `%${q.q}%`); }
    sql += ' ORDER BY category, name_cn';
    const limit = Math.min(parseInt(q.limit) || 50, 200);
    const offset = parseInt(q.offset) || 0;
    sql += ` LIMIT ${limit} OFFSET ${offset}`;
    const rows = db.prepare(sql).all(...params);
    const total = db.prepare('SELECT COUNT(*) as cnt FROM species WHERE 1=1' + 
      (q.category ? ' AND category = ?' : '')).get(...(q.category ? [q.category] : [])).cnt;
    res.json({ ok: true, data: rows, total, limit, offset });
  });

  // GET /api/v2/species/:id — 物种详情
  app.get('/api/v2/species/:id', (req, res) => {
    const sp = db.prepare('SELECT * FROM species WHERE species_id = ?').get(req.params.id);
    if (!sp) return res.status(404).json({ ok: false, error: '物种不存在' });
    res.json({ ok: true, data: sp });
  });

  // GET /api/v2/species/:id/morphs — 获取物种的所有品系
  app.get('/api/v2/species/:id/morphs', (req, res) => {
    const genes = db.prepare(`
      SELECT g.* FROM species_morphs sm
      JOIN morph_genes g ON sm.gene_id = g.gene_id
      WHERE sm.species_id = ?
      ORDER BY g.inheritance, g.gene_name
    `).all(req.params.id);
    
    const combos = db.prepare(`
      SELECT * FROM morph_combinations WHERE species_id = ?
      ORDER BY combo_name
    `).all(req.params.id);
    
    res.json({ ok: true, data: { genes, combos, total_genes: genes.length, total_combos: combos.length } });
  });

  // GET /api/v2/morphs/genes — 列出所有基因（支持 species_id 过滤）
  app.get('/api/v2/morphs/genes', (req, res) => {
    const q = req.query || {};
    let sql = 'SELECT g.*, s.name_cn as species_name FROM morph_genes g';
    let countSql = 'SELECT COUNT(*) as cnt FROM morph_genes g';
    
    if (q.species_id) {
      sql += ' JOIN species_morphs sm ON g.gene_id = sm.gene_id JOIN species s ON sm.species_id = s.species_id WHERE sm.species_id = ?';
      countSql += ' JOIN species_morphs sm ON g.gene_id = sm.gene_id WHERE sm.species_id = ?';
      const rows = db.prepare(sql).all(q.species_id);
      const total = db.prepare(countSql).get(q.species_id).cnt;
      return res.json({ ok: true, data: rows, total });
    }
    
    sql += ' LEFT JOIN species_morphs sm ON g.gene_id = sm.gene_id LEFT JOIN species s ON sm.species_id = s.species_id ORDER BY g.gene_name';
    const rows = db.prepare(sql).all();
    const total = db.prepare('SELECT COUNT(*) as cnt FROM morph_genes').get().cnt;
    res.json({ ok: true, data: rows, total });
  });

  // GET /api/v2/morphs/combos — 列出组合品系（支持 species_id 过滤）
  app.get('/api/v2/morphs/combos', (req, res) => {
    const q = req.query || {};
    let sql = 'SELECT c.*, s.name_cn as species_name FROM morph_combinations c JOIN species s ON c.species_id = s.species_id';
    let countSql = 'SELECT COUNT(*) as cnt FROM morph_combinations';
    const params = [];
    
    if (q.species_id) {
      sql += ' WHERE c.species_id = ?';
      countSql += ' WHERE species_id = ?';
      params.push(q.species_id);
    }
    sql += ' ORDER BY c.combo_name';
    
    const rows = db.prepare(sql).all(...params);
    const total = db.prepare(countSql).get(...params).cnt;
    res.json({ ok: true, data: rows, total });
  });

  // POST /api/v2/morphs/calculate — 基因计算器
  app.post('/api/v2/morphs/calculate', (req, res) => {
    const { parent1, parent2, species_id } = req.body || {};
    if (!parent1 || !parent2) {
      return res.status(400).json({ ok: false, error: '需要 parent1 和 parent2 基因型' });
    }

    // Call Python genecalc
    const { execSync } = require('child_process');
    try {
      const cmd = `python3 scripts/genecalc.py ${JSON.stringify(parent1)} ${JSON.stringify(parent2)}`;
      const output = execSync(cmd, { cwd: require('path').join(__dirname, '..'), timeout: 10000, encoding: 'utf-8' });
      res.json({ ok: true, data: { text: output.trim() } });
    } catch (e) {
      res.status(500).json({ ok: false, error: '计算失败: ' + e.message });
    }
  });

  // GET /api/v2/morphs/heavy — 获取所有 morph_heavy 品种
  app.get('/api/v2/morphs/heavy', (req, res) => {
    const rows = db.prepare(`
      SELECT s.species_id, s.name_cn, s.name_latin, s.category,
             COUNT(sm.morph_id) as morph_count
      FROM species s
      LEFT JOIN species_morphs sm ON s.species_id = sm.species_id
      WHERE json_extract(s.traits, '$.morph_heavy') = 1
        OR s.name_latin IN ('Pantherophis guttatus%','Python regius%','Eublepharis macularius%')
      GROUP BY s.species_id
      ORDER BY morph_count DESC
    `).all();
    res.json({ ok: true, data: rows });
  });
};
