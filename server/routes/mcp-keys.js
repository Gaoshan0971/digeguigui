const { adminKey } = require('../config');
// routes/mcp-keys.js — API Key 管理 (MCP Server)
// 设计原则：Agent 自服务 — 无需人类点网页，纯 REST API 闭环
const path = require('path');

function register(app) {
  const db = require('../db');

  // ── 公开发：Agent 查自己的 Key 信息 ──
  app.get('/api/mcp-keys/info', (req, res) => {
    const key = (req.headers['x-api-key'] || req.headers['authorization']?.replace('Bearer ', '') || '').trim();
    if (!key) return res.status(400).json({ ok: false, error: '请提供 x-api-key header' });

    const row = db.prepare(
      'SELECT name, tier, rate_limit, created_at, expires_at, revoked, last_used FROM api_keys WHERE key_hash = ?'
    ).get(key);

    if (!row || row.revoked) return res.status(401).json({ ok: false, error: 'Key 无效或已吊销' });

    res.json({
      ok: true,
      key_info: {
        name: row.name,
        tier: row.tier,
        rate_limit: row.rate_limit,
        created_at: row.created_at,
        expires_at: row.expires_at,
        last_used: row.last_used,
      },
      tiers: {
        free: { rate: '10次/分钟', tools: ['全部9个工具：搜索/档案/识龟/估价/基因/饲养反查/健康/统计'], locked: ['verify_provenance'], upgrade_to: 'pro' },
        pro: { rate: '60次/分钟', tools: ['全部10个工具含身份验证'], upgrade_to: 'enterprise' },
        enterprise: { rate: '定制', tools: ['全部 + 数据导出 + 私有部署'], contact: 'https://digeguigui.com' },
      },
    });
  });

  // ── 公开发：Agent 一键申请免费 Key ──
  app.post('/api/mcp-keys/apply', (req, res) => {
    if (!req.body) return readBody(req, res, handleApply);
    handleApply(req, res);
  });
  async function handleApply(req, res) {
    const { name } = req.body || {};
    if (!name || name.trim().length < 2) return res.status(400).json({ ok: false, error: '请填写 name（至少2字符，如 "my-agent"）' });

    // IP 限速：每 IP 每天最多 3 个免费 Key
    const ip = (req.headers['x-forwarded-for'] || req.headers['x-real-ip'] || req.socket?.remoteAddress || 'unknown').split(',')[0].trim();
    const today = new Date().toISOString().slice(0, 10);
    const todayCount = db.prepare(
      "SELECT COUNT(*) as cnt FROM api_keys WHERE created_by = 'apply' AND created_at >= ?"
    ).get(today);
    // 简化：用 created_at 前缀匹配今天
    const recentCount = db.prepare(
      "SELECT COUNT(*) as cnt FROM api_keys WHERE tier = 'free' AND created_at LIKE ?"
    ).get(today + '%');
    if ((recentCount?.cnt || 0) >= 100) {
      return res.status(429).json({ ok: false, error: '今日免费 Key 已达上限(100个/天)，请明天再试或联系升级 Pro' });
    }

    const crypto = require('crypto');
    const random = crypto.randomBytes(10).toString('hex');
    const keyHash = `dg-fre-${random}`;

    try {
      db.prepare(
        `INSERT INTO api_keys (key_hash, name, tier, rate_limit, contact, created_by)
         VALUES (?, ?, 'free', 10, ?, 'apply')`
      ).run(keyHash, name.trim(), ip);

      res.json({
        ok: true,
        api_key: keyHash,
        tier: 'free',
        rate_limit: '10次/分钟',
        available_tools: ['search_species', 'get_species_profile', 'identify_turtle', 'estimate_value', 'genetics_calculator', 'db_stats', 'search_by_traits', 'health_check'],
        locked_tools: ['verify_provenance'],
        unlock_hint: '身份验证功能需升级 Pro。60次/分钟，联系 https://digeguigui.com',
        usage: `Header: x-api-key: ${keyHash}  或  Authorization: Bearer ${keyHash}`,
      });
    } catch (e) {
      res.status(500).json({ ok: false, error: e.message });
    }
  }

  // ── 管理端：Key 列表 ──
  app.get('/api/admin/mcp-keys', (req, res) => {
    const q = new URL(req.url, 'http://localhost').searchParams;
    if (q.get('admin_key') !== adminKey) return res.status(403).json({ ok: false, error: 'Unauthorized' });

    const rows = db.prepare(
      'SELECT id, key_hash, name, tier, rate_limit, contact, created_at, expires_at, revoked, last_used FROM api_keys ORDER BY id DESC'
    ).all();

    res.json({ ok: true, keys: rows, total: rows.length });
  });

  // ── 管理端：生成 Key（可指定 tier/limit） ──
  app.post('/api/admin/mcp-keys', (req, res) => {
    if (!req.body) return readBody(req, res, handleCreate);
    handleCreate(req, res);
  });
  async function handleCreate(req, res) {
    const { admin_key, name, tier, rate_limit, contact, expires_at } = req.body || {};
    if (admin_key !== adminKey) return res.status(403).json({ ok: false, error: 'Unauthorized' });
    if (!name) return res.status(400).json({ ok: false, error: 'name required' });

    const crypto = require('crypto');
    const tierPrefix = (tier || 'free').substring(0, 3);
    const random = crypto.randomBytes(12).toString('hex');
    const keyHash = `dg-${tierPrefix}-${random}`;

    try {
      db.prepare(
        `INSERT INTO api_keys (key_hash, name, tier, rate_limit, contact, expires_at, created_by)
         VALUES (?, ?, ?, ?, ?, ?, 'admin')`
      ).run(keyHash, name, tier || 'free', rate_limit || 10, contact || '', expires_at || null);

      res.json({
        ok: true,
        key: { key_hash: keyHash, name, tier: tier || 'free', rate_limit: rate_limit || 10 },
        message: 'Key 已生成。请妥善保管，丢失不可找回。',
      });
    } catch (e) {
      res.status(500).json({ ok: false, error: e.message });
    }
  }

  // ── 管理端：吊销 Key ──
  app.delete('/api/admin/mcp-keys/:id', (req, res) => {
    if (!req.body) return readBody(req, res, handleRevoke);
    handleRevoke(req, res);
  });
  async function handleRevoke(req, res) {
    const { admin_key } = req.body || {};
    if (admin_key !== adminKey) return res.status(403).json({ ok: false, error: 'Unauthorized' });

    const id = req.params?.id;
    const result = db.prepare('UPDATE api_keys SET revoked = 1 WHERE id = ?').run(id);
    res.json({ ok: true, revoked: result.changes > 0 });
  }

  console.log('[mcp-keys] Routes registered');
}

function readBody(req, res, callback) {
  let body = '';
  req.on('data', chunk => { body += chunk; });
  req.on('end', () => {
    try { req.body = JSON.parse(body); } catch (e) { req.body = {}; }
    callback(req, res);
  });
}

module.exports = { register };
