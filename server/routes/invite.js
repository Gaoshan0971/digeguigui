// routes/invite.js — 达人邀请码生成 / 核销
const db = require('../db');
const crypto = require('crypto');
const { spawn } = require('child_process');
const path = require('path');

const ADMIN_KEY = 'turtle-admin-2026';
const SHARE_CARD_SCRIPT = path.join(__dirname, '..', '..', 'scripts', 'share_card.py');
const PYTHON = '/usr/bin/python3';

function genCode() {
  const chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'; // no 0/O/1/I to avoid confusion
  let code = '';
  for (let i = 0; i < 6; i++) code += chars[crypto.randomInt(0, chars.length)];
  return 'TG-' + code; // TG- prefix = 兔龟
}

function register(app) {

  // POST /api/admin/invite-codes/generate — 批量生成邀请码（管理端）
  app.post('/api/admin/invite-codes/generate', async (req, res) => {
    const { admin_key = '', count = 10, created_by = '', avatar_url = '' } = req.body || {};
    if (admin_key !== ADMIN_KEY) return res.status(403).json({ ok: false, error: '无权访问' });

    const batchId = 'B' + Date.now().toString(36).toUpperCase();
    const codes = [];
    const stmt = db.prepare('INSERT INTO invite_codes (code, batch_id, created_by) VALUES (?, ?, ?)');

    for (let i = 0; i < count; i++) {
      let code = genCode();
      // 防碰撞重试
      for (let retry = 0; retry < 5; retry++) {
        const existing = db.prepare('SELECT code_id FROM invite_codes WHERE code = ?').get(code);
        if (!existing) break;
        code = genCode();
      }
      stmt.run(code, batchId, created_by);
      codes.push(code);
    }

    // 生成达人分享卡
    let shareCardUrl = '';
    if (created_by) {
      shareCardUrl = await new Promise((resolve) => {
        try {
          const dummyImg = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPj/HwADBwIAMCbHYQAAAABJRU5ErkJggg==';
          const py = spawn(PYTHON, [SHARE_CARD_SCRIPT]);
          let stdout = '', stderr = '';
          py.stdin.write(JSON.stringify({
            image_base64: dummyImg,
            species_name: '免费领证',
            title: '尊敬的爬圈大佬',
            subtitle: '滴个龟龟免费赠送您10个爬宠身份证名额',
            footer: '快给宝贝上个户口吧！先抢先得！',
            brand: '滴个龟龟 · 达人邀请'
          }));
          py.stdin.end();
          py.stdout.on('data', d => stdout += d);
          py.stderr.on('data', d => stderr += d);
          py.on('close', code => {
            if (code === 0) {
              try { resolve(JSON.parse(stdout).url || ''); } catch { resolve(''); }
            } else {
              resolve('');
            }
          });
          py.on('error', () => resolve(''));
        } catch { resolve(''); }
      });
    }

    res.json({
      ok: true,
      data: {
        batch_id: batchId,
        codes,
        created_by,
        share_card_url: shareCardUrl,
        share_path: `/pages/claim/claim?batch_id=${batchId}`,
        share_title: '尊敬的爬圈大佬'
      }
    });
  });

  // GET /api/admin/invite-codes/batches — 批次列表（管理端）
  app.get('/api/admin/invite-codes/batches', (req, res) => {
    const { admin_key = '' } = req.query;
    if (admin_key !== ADMIN_KEY) return res.status(403).json({ ok: false, error: '无权访问' });

    const batches = db.prepare(`
      SELECT batch_id, created_by, COUNT(*) as total,
        SUM(CASE WHEN used_by != '' THEN 1 ELSE 0 END) as used,
        MIN(created_at) as created_at
      FROM invite_codes
      GROUP BY batch_id
      ORDER BY created_at DESC
      LIMIT 20
    `).all();

    res.json({ ok: true, data: batches });
  });

  // GET /api/admin/invite-codes/:batch_id — 批次详情（管理端）
  app.get('/api/admin/invite-codes/:batch_id', (req, res) => {
    const { admin_key = '' } = req.query;
    if (admin_key !== ADMIN_KEY) return res.status(403).json({ ok: false, error: '无权访问' });

    const codes = db.prepare(`
      SELECT code, used_by, used_at, created_at
      FROM invite_codes WHERE batch_id = ?
      ORDER BY code_id
    `).all(req.params.batch_id);

    res.json({ ok: true, data: { batch_id: req.params.batch_id, codes } });
  });

  // POST /api/provenance/redeem-check — 仅验证邀请码（不核销）
  app.post('/api/provenance/redeem-check', (req, res) => {
    const { code } = req.body || {};
    if (!code) return res.status(400).json({ ok: false, error: '请输入邀请码' });

    const row = db.prepare('SELECT * FROM invite_codes WHERE code = ?').get(code.toUpperCase());
    if (!row) return res.json({ ok: true, data: { valid: false, error: '邀请码无效' } });
    if (row.used_by) return res.json({ ok: true, data: { valid: false, error: '该邀请码已被使用' } });

    res.json({ ok: true, data: { valid: true, batch_id: row.batch_id } });
  });

  // POST /api/provenance/redeem — 使用邀请码免费领证
  app.post('/api/provenance/redeem', (req, res) => {
    const { code, user_token = '' } = req.body || {};
    if (!code) return res.status(400).json({ ok: false, error: '请输入邀请码' });

    const row = db.prepare('SELECT * FROM invite_codes WHERE code = ?').get(code);
    if (!row) return res.status(404).json({ ok: false, error: '邀请码无效' });
    if (row.used_by) return res.status(400).json({ ok: false, error: '该邀请码已被使用' });

    // 标记已用
    db.prepare(`
      UPDATE invite_codes SET used_by = ?, used_at = datetime('now','localtime')
      WHERE code = ?
    `).run(user_token || 'anonymous', code);

    res.json({
      ok: true,
      data: { code, batch_id: row.batch_id, message: '核销成功 · 免费领证已激活' }
    });
  });

  // GET /api/invite-codes/batch/:batchId — 公开查批次余额
  app.get('/api/invite-codes/batch/:batchId', (req, res) => {
    const batchId = req.params.batchId;
    const total = db.prepare('SELECT COUNT(*) as cnt FROM invite_codes WHERE batch_id = ?').get(batchId);
    const used = db.prepare("SELECT COUNT(*) as cnt FROM invite_codes WHERE batch_id = ? AND used_at != ''").get(batchId);
    const remaining = total.cnt - used.cnt;

    if (total.cnt === 0) {
      return res.json({ ok: false, error: '批次不存在' });
    }

    res.json({
      ok: true,
      data: {
        batch_id: batchId,
        total: total.cnt,
        used: used.cnt,
        remaining,
        all_gone: remaining === 0
      }
    });
  });

  // POST /api/invite-codes/claim — 一键领码（自动分配下一个可用码）
  app.post('/api/invite-codes/claim', (req, res) => {
    const { batch_id, token = '' } = req.body || {};
    if (!batch_id) return res.status(400).json({ ok: false, error: '缺少批次ID' });

    // 如果该用户已领过，返回同一个码（防刷新丢失）
    if (token) {
      const existing = db.prepare(
        "SELECT code FROM invite_codes WHERE batch_id = ? AND used_by = ? AND used_at != ''"
      ).get(batch_id, token);
      if (existing) {
        return res.json({ ok: true, data: { code: existing.code, already_claimed: true } });
      }
    }

    // 领下一个未使用的码（原子操作）
    const row = db.prepare(
      "SELECT code_id, code FROM invite_codes WHERE batch_id = ? AND used_at = '' ORDER BY code_id LIMIT 1"
    ).get(batch_id);

    if (!row) {
      return res.json({ ok: false, error: '已抢完', all_gone: true });
    }

    db.prepare(
      "UPDATE invite_codes SET used_by = ?, used_at = datetime('now','localtime') WHERE code_id = ?"
    ).run(token || 'claimant', row.code_id);

    res.json({
      ok: true,
      data: { code: row.code, already_claimed: false }
    });
  });
}

module.exports = { register };
