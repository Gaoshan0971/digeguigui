// routes/prices.js — 价格查询 API
module.exports.register = function(app) {
  const db = require('../db');

  // GET /api/v2/prices/species/:id — 物种价格
  app.get('/api/v2/prices/species/:id', (req, res) => {
    const sp = db.prepare('SELECT * FROM species_prices WHERE species_id = ?').get(req.params.id);
    if (!sp) return res.json({ ok: true, data: null, note: '暂无价格数据' });
    res.json({ ok: true, data: sp });
  });

  // GET /api/v2/prices/morphs?species_id=X — 品系价格
  app.get('/api/v2/prices/morphs', (req, res) => {
    const q = req.query || {};
    let sql = `
      SELECT mp.*, 
        COALESCE(g.gene_symbol, c.combo_name) as symbol,
        COALESCE(g.gene_name_cn, c.combo_name_cn) as name_cn,
        CASE WHEN mp.gene_id IS NOT NULL THEN 'gene' ELSE 'combo' END as type
      FROM morph_prices mp
      LEFT JOIN morph_genes g ON mp.gene_id = g.gene_id
      LEFT JOIN morph_combinations c ON mp.combo_id = c.combo_id
      WHERE 1=1
    `;
    const params = [];
    if (q.species_id) { sql += ' AND mp.species_id = ?'; params.push(q.species_id); }
    if (q.rarity) { sql += ' AND mp.rarity = ?'; params.push(q.rarity); }
    sql += ' ORDER BY mp.price_range_high DESC';
    const rows = db.prepare(sql).all(...params);
    res.json({ ok: true, data: rows, total: rows.length });
  });

  // GET /api/v2/prices/estimate — 估价接口
  // query: species_id, gene_symbols=[], combo_name, grade=normal|select|premium, sex=male|female|unknown
  app.get('/api/v2/prices/estimate', (req, res) => {
    const q = req.query || {};
    const sid = parseInt(q.species_id) || 0;
    const grade = q.grade || 'select';
    const genes = q.genes ? q.genes.split(',') : [];
    const combo = q.combo || '';
    
    if (!sid) return res.status(400).json({ ok: false, error: '需要 species_id' });
    
    const spPrice = db.prepare('SELECT * FROM species_prices WHERE species_id = ?').get(sid);
    const spInfo = db.prepare('SELECT name_cn, name_latin, category FROM species WHERE species_id = ?').get(sid);
    if (!spInfo) return res.status(404).json({ ok: false, error: '物种不存在' });
    
    let baseLow = 0, baseHigh = 0;
    if (spPrice) {
      if (grade === 'normal') { baseLow = spPrice.normal_low; baseHigh = spPrice.normal_high; }
      else if (grade === 'premium') { baseLow = spPrice.premium_low; baseHigh = spPrice.premium_high; }
      else { baseLow = spPrice.select_low; baseHigh = spPrice.select_high; }
    }
    
    let morphPremium = 0;
    let morphDetails = [];
    
    // Add gene premiums
    for (const gsym of genes) {
      const gene = db.prepare("SELECT gene_id FROM morph_genes WHERE gene_symbol = ?").get(gsym.trim());
      if (!gene) continue;
      const gp = db.prepare("SELECT * FROM morph_prices WHERE gene_id = ? AND species_id = ?").get(gene.gene_id, sid);
      if (gp && gp.visual_price) {
        morphPremium += gp.visual_price;
        morphDetails.push({ type: 'gene', symbol: gsym, premium: gp.visual_price, rarity: gp.rarity });
      }
    }
    
    // Add combo premium
    if (combo) {
      const cp = db.prepare(`
        SELECT mp.*, c.combo_name FROM morph_prices mp 
        JOIN morph_combinations c ON mp.combo_id = c.combo_id 
        WHERE c.combo_name = ? AND mp.species_id = ?
      `).get(combo, sid);
      if (cp) {
        morphPremium = Math.max(morphPremium, (cp.price_range_low + cp.price_range_high) / 2);
        morphDetails.push({ type: 'combo', name: combo, premium: morphPremium, rarity: cp.rarity });
      }
    }
    
    const estLow = Math.round((baseLow + morphPremium) * 0.8);
    const estHigh = Math.round((baseHigh + morphPremium) * 1.2);
    
    res.json({
      ok: true,
      data: {
        species: spInfo.name_cn,
        grade,
        base_price: baseLow > 0 ? `¥${baseLow}-${baseHigh}` : '暂无',
        morph_premium: morphPremium > 0 ? `¥${morphPremium}` : '无',
        estimated: `¥${estLow}-${estHigh}`,
        confidence: spPrice ? '中' : '低（无基础定价）',
        breakdown: morphDetails,
      }
    });
  });
};
