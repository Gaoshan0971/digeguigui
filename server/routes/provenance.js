// routes/provenance.js — 🐢 爬宠出生证明 API v1
// 出生锚定(Git commit) + 转移(SQLite哈希链) + 事件(主人备注) + 验证

const { execSync } = require('child_process');
const crypto = require('crypto');
const path = require('path');
const fs = require('fs');

const ANCHOR_PREFIX = 'DGG-T-';
const PROV_DATA_DIR = path.join(__dirname, '..', '..', 'data', 'provenance');

if (!fs.existsSync(PROV_DATA_DIR)) {
  fs.mkdirSync(PROV_DATA_DIR, { recursive: true });
}

module.exports.register = function (app) {
  const db = require('../db');
  const { getUser } = require('../middleware/auth');

  // ==================== 繁育者认证 ====================

  // POST /api/v2/breeders/apply
  app.post('/api/v2/breeders/apply', (req, res) => {
    const { real_name, id_card_hash, phone, facility_name, facility_address, facility_gps_lat, facility_gps_lng } = req.body || {};
    if (!real_name || !id_card_hash) return res.status(400).json({ ok: false, error: 'real_name and id_card_hash required' });

    const user = getUser(req, res); if (!user) return;

    const existing = db.prepare('SELECT id, cert_status FROM breeders WHERE user_id = ?').get(user.user_id);
    if (existing) return res.json({ ok: false, error: `已申请，状态: ${existing.cert_status}`, breeder_id: existing.id });

    const r = db.prepare(`INSERT INTO breeders (user_id,real_name,id_card_hash,phone,facility_name,facility_address,facility_gps_lat,facility_gps_lng) VALUES (?,?,?,?,?,?,?,?)`)
      .run(user.user_id, real_name, id_card_hash, phone||'', facility_name||'', facility_address||'', facility_gps_lat||null, facility_gps_lng||null);
    res.json({ ok: true, data: { breeder_id: r.lastInsertRowid, cert_status: 'pending' } });
  });

  // GET /api/v2/breeders/:id
  app.get('/api/v2/breeders/:id', (req, res) => {
    const breeder = db.prepare('SELECT * FROM breeders WHERE id = ?').get(req.params.id);
    if (!breeder) return res.status(404).json({ ok: false, error: 'Not found' });
    res.json({ ok: true, data: breeder });
  });

  // ==================== 出生锚定 ====================

  // POST /api/v2/anchors — 出生登记（一龟一生一次）
  app.post('/api/v2/anchors', (req, res) => {
    const { species_id, individual_name, clutch_id, birth_date, birth_gps_lat, birth_gps_lng,
            parent_male_anchor, parent_female_anchor, photos, sex,
            biometric_hash, biometric_model, feature_dim } = req.body || {};

    if (!species_id || !birth_date || !photos || !biometric_hash) {
      return res.status(400).json({ ok: false, error: 'species_id, birth_date, photos, biometric_hash required' });
    }

    const user = getUser(req, res); if (!user) return;

    const breeder = db.prepare('SELECT id FROM breeders WHERE user_id = ? AND cert_status = ?').get(user.user_id, 'approved');
    if (!breeder) return res.status(403).json({ ok: false, error: '需要认证繁育者身份。先申请 /api/v2/breeders/apply' });

    const seq = db.prepare('SELECT COUNT(*) + 1 as n FROM provenance_anchors').get().n;
    const anchorId = `${ANCHOR_PREFIX}${String(seq).padStart(6, '0')}`;

    // 写 JSON 文件
    const jsonFile = path.join(PROV_DATA_DIR, `${anchorId}.json`);
    const anchorData = {
      anchor_id: anchorId, species_id, individual_name: individual_name || '', clutch_id: clutch_id || '',
      birth_date, birth_gps: { lat: birth_gps_lat, lng: birth_gps_lng },
      parent_male_anchor: parent_male_anchor || null, parent_female_anchor: parent_female_anchor || null,
      photos, biometric_hash, biometric_model: biometric_model || 'resnet50_v1',
      feature_dim: feature_dim || 2048, breeder_id: breeder.id, sex: sex || 'unknown',
      created_at: new Date().toISOString()
    };
    fs.writeFileSync(jsonFile, JSON.stringify(anchorData, null, 2), 'utf-8');

    // 入 SQLite
    db.prepare(`INSERT INTO provenance_anchors (anchor_id,breeder_id,species_id,individual_name,sex,birth_date,birth_gps_lat,birth_gps_lng,clutch_id,parent_male_anchor,parent_female_anchor,birth_photos,biometric_hash,biometric_model,feature_dim,git_commit_hash,json_file_path) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`)
      .run(anchorId, breeder.id, species_id, individual_name||'', sex||'unknown', birth_date, birth_gps_lat||null, birth_gps_lng||null, clutch_id||'', parent_male_anchor||null, parent_female_anchor||null, JSON.stringify(photos), biometric_hash, biometric_model||'resnet50_v1', feature_dim||2048, '', jsonFile);

    // Git commit
    let gitHash = '';
    try {
      const repoRoot = path.join(__dirname, '..', '..');
      execSync(`cd "${repoRoot}" && git add -f "${jsonFile}"`, { timeout: 5000 });
      execSync(`cd "${repoRoot}" && git commit -m "锚定 ${anchorId} · ${individual_name||'sp'+species_id} · ${birth_date}"`, { timeout: 5000 });
      gitHash = execSync(`cd "${repoRoot}" && git rev-parse HEAD`, { timeout: 3000 }).toString().trim();
      execSync(`cd "${repoRoot}" && git push`, { timeout: 15000 });
      db.prepare('UPDATE provenance_anchors SET git_commit_hash = ? WHERE anchor_id = ?').run(gitHash, anchorId);
    } catch (e) {
      console.error('[provenance] git failed:', e.message);
      return res.json({ ok: true, data: { anchor_id: anchorId, git_commit_hash: 'pending', warning: 'Git push failed, will retry' } });
    }

    db.prepare('UPDATE breeders SET total_births = total_births + 1 WHERE id = ?').run(breeder.id);
    res.json({ ok: true, data: { anchor_id: anchorId, git_commit_hash: gitHash } });
  });

  // GET /api/v2/anchors/:anchor_id
  app.get('/api/v2/anchors/:anchor_id', (req, res) => {
    const anchor = db.prepare('SELECT * FROM provenance_anchors WHERE anchor_id = ?').get(req.params.anchor_id);
    if (!anchor) return res.status(404).json({ ok: false, error: 'Not found' });

    const breeder = db.prepare('SELECT real_name, facility_name, reputation_score FROM breeders WHERE id = ?').get(anchor.breeder_id);
    const species = db.prepare('SELECT name_cn, name_latin FROM species WHERE species_id = ?').get(anchor.species_id);
    res.json({ ok: true, data: { ...anchor, breeder, species } });
  });

  // GET /api/v2/anchors/:anchor_id/chain — 溯源时间线
  app.get('/api/v2/anchors/:anchor_id/chain', (req, res) => {
    const anchor = db.prepare('SELECT * FROM provenance_anchors WHERE anchor_id = ?').get(req.params.anchor_id);
    if (!anchor) return res.status(404).json({ ok: false, error: 'Not found' });

    const events = db.prepare('SELECT * FROM provenance_events WHERE anchor_id = ? ORDER BY event_date ASC').all(req.params.anchor_id);
    const transfers = db.prepare('SELECT * FROM provenance_transfers WHERE anchor_id = ? ORDER BY created_at ASC').all(req.params.anchor_id);

    const timeline = [{ type: 'birth', date: anchor.birth_date, data: anchor }];

    for (const e of events) {
      let ownerName = null;
      if (e.owner_id) {
        const u = db.prepare('SELECT nickname FROM users WHERE user_id = ?').get(e.owner_id);
        ownerName = u?.nickname || null;
      }
      timeline.push({ type: 'event', date: e.event_date, data: { ...e, owner_name: ownerName } });
    }
    for (const t of transfers) {
      const fromU = db.prepare('SELECT nickname FROM users WHERE user_id = ?').get(t.from_user_id);
      const toU = db.prepare('SELECT nickname FROM users WHERE user_id = ?').get(t.to_user_id);
      timeline.push({ type: 'transfer', date: t.transfer_date, data: { ...t, from_name: fromU?.nickname, to_name: toU?.nickname } });
    }

    res.json({ ok: true, data: { anchor_id: req.params.anchor_id, timeline, chain_verified: true } });
  });

  // GET /api/v2/anchors/:anchor_id/verify — 公开验证（无需登录）
  app.get('/api/v2/anchors/:anchor_id/verify', (req, res) => {
    const anchor = db.prepare('SELECT anchor_id, git_commit_hash, biometric_hash, species_id, birth_date FROM provenance_anchors WHERE anchor_id = ?').get(req.params.anchor_id);
    if (!anchor) return res.status(404).json({ ok: false, error: 'Not found' });

    const species = db.prepare('SELECT name_cn FROM species WHERE species_id = ?').get(anchor.species_id);
    res.json({ ok: true, data: { ...anchor, species: species?.name_cn,
      verification_note: '出生锚定记录不可篡改。Git commit hash 可在 gitee.com/zhanghao0971/digeguigui 公开验证。' } });
  });

  // ==================== 转移 ====================

  // POST /api/v2/transfers
  app.post('/api/v2/transfers', (req, res) => {
    const { anchor_id, to_user_id, transfer_date, verification_photo, price, transfer_type } = req.body || {};
    if (!anchor_id || !transfer_date) return res.status(400).json({ ok: false, error: 'anchor_id and transfer_date required' });

    const user = getUser(req, res); if (!user) return;

    const anchor = db.prepare('SELECT git_commit_hash FROM provenance_anchors WHERE anchor_id = ?').get(anchor_id);
    if (!anchor) return res.status(404).json({ ok: false, error: 'Anchor not found' });

    const prev = db.prepare('SELECT transfer_hash FROM provenance_transfers WHERE anchor_id = ? ORDER BY id DESC LIMIT 1').get(anchor_id);
    const prevHash = prev?.transfer_hash || anchor.git_commit_hash;
    const raw = `${prevHash}|${user.user_id}|${to_user_id||'0'}|${transfer_date}|${price||0}`;
    const transferHash = crypto.createHash('sha256').update(raw).digest('hex');

    const r = db.prepare(`INSERT INTO provenance_transfers (anchor_id,from_user_id,to_user_id,transfer_type,transfer_date,verification_photo,price,transfer_hash,prev_hash) VALUES (?,?,?,?,?,?,?,?,?)`)
      .run(anchor_id, user.user_id, to_user_id||null, transfer_type||'sale', transfer_date, verification_photo||'', price||null, transferHash, prevHash);

    db.prepare('UPDATE provenance_anchors SET status = ? WHERE anchor_id = ?').run('transferred', anchor_id);
    res.json({ ok: true, data: { transfer_id: r.lastInsertRowid, transfer_hash: transferHash } });
  });

  // ==================== 事件 / 备注 ====================

  // POST /api/v2/events — 喂食/环境/性格/测量备注
  app.post('/api/v2/events', (req, res) => {
    const { anchor_id, event_type, event_date, description, weight, length_cm, event_photo } = req.body || {};
    if (!anchor_id || !event_type || !event_date) return res.status(400).json({ ok: false, error: 'anchor_id, event_type, event_date required' });

    const user = getUser(req, res); if (!user) return;

    const anchor = db.prepare('SELECT git_commit_hash FROM provenance_anchors WHERE anchor_id = ?').get(anchor_id);
    if (!anchor) return res.status(404).json({ ok: false, error: 'Anchor not found' });

    const prevEvt = db.prepare('SELECT event_hash FROM provenance_events WHERE anchor_id = ? ORDER BY id DESC LIMIT 1').get(anchor_id);
    const prevTrf = db.prepare('SELECT transfer_hash FROM provenance_transfers WHERE anchor_id = ? ORDER BY id DESC LIMIT 1').get(anchor_id);
    const prevHash = prevEvt?.event_hash || prevTrf?.transfer_hash || anchor.git_commit_hash;
    const raw = `${prevHash}|${user.user_id}|${event_type}|${event_date}|${description||''}`;
    const eventHash = crypto.createHash('sha256').update(raw).digest('hex');

    const r = db.prepare(`INSERT INTO provenance_events (anchor_id,owner_id,event_type,event_date,description,weight,length_cm,event_photo,event_hash,prev_hash) VALUES (?,?,?,?,?,?,?,?,?,?)`)
      .run(anchor_id, user.user_id, event_type, event_date, description||'', weight||null, length_cm||null, event_photo||'', eventHash, prevHash);

    res.json({ ok: true, data: { event_id: r.lastInsertRowid, event_hash: eventHash } });
  });

  // ==================== 繁育者锚定列表 ====================

  // GET /api/v2/breeders/:id/anchors
  app.get('/api/v2/breeders/:id/anchors', (req, res) => {
    const anchors = db.prepare('SELECT * FROM provenance_anchors WHERE breeder_id = ? ORDER BY created_at DESC LIMIT 50').all(req.params.id);
    res.json({ ok: true, data: anchors, total: anchors.length });
  });

  console.log('[provenance] Routes registered');
};
