// index.js — 滴个龟龟 API 服务入口
const http = require('http');
const db = require('./db');

const PORT = process.env.PORT || 3456;

// ==================== 简易路由 ====================

const routes = [];

function get(path, handler) { routes.push({ method: 'GET', path, handler }); }
function post(path, handler) { routes.push({ method: 'POST', path, handler }); }
function put(path, handler) { routes.push({ method: 'PUT', path, handler }); }
function del(path, handler) { routes.push({ method: 'DELETE', path, handler }); }

// 路由匹配（支持 :id 参数）
function matchRoute(method, url) {
  const urlPath = url.split('?')[0];
  for (const r of routes) {
    if (r.method !== method) continue;
    const pattern = r.path.replace(/:(\w+)/g, '([^/]+)');
    const m = urlPath.match(new RegExp(`^${pattern}$`));
    if (m) {
      const params = {};
      const keys = [...r.path.matchAll(/:(\w+)/g)].map(k => k[1]);
      keys.forEach((k, i) => params[k] = m[i + 1]);
      return { handler: r.handler, params };
    }
  }
  return null;
}

// 将 get/post/put/delete 挂到 app 上
const app = { get, post, put, delete: del };

// 注册路由模块
require('./routes/species').register(app);
require('./routes/collections').register(app);
require('./routes/appraisals').register(app);
require('./routes/breedings').register(app);
require('./routes/identify').register(app);
require('./routes/dataset').register(app);
require('./routes/appraise-ai').register(app);
require('./routes/morphs').register(app);
require('./routes/prices').register(app);
require('./routes/provenance').register(app);
require('./routes/payments').register(app);
require('./routes/labeling').register(app);

// 注册用户路由
app.post('/api/users/login', (req, res) => {
  const { openid, nickname = '', avatar_url = '' } = req.body || {};
  if (!openid) return send(res, 400, { ok: false, error: '缺少 openid' });

  let user = db.prepare('SELECT * FROM users WHERE openid = ?').get(openid);
  if (!user) {
    db.prepare('INSERT INTO users (openid, nickname, avatar_url) VALUES (?, ?, ?)').run(openid, nickname, avatar_url);
    user = db.prepare('SELECT * FROM users WHERE openid = ?').get(openid);
  } else if (nickname || avatar_url) {
    db.prepare('UPDATE users SET nickname = COALESCE(?, nickname), avatar_url = COALESCE(?, avatar_url) WHERE user_id = ?')
      .run(nickname || null, avatar_url || null, user.user_id);
  }

  send(res, 200, { ok: true, data: { user, token: openid } }); // token = openid（MVP 阶段）
});

// 点赞
app.post('/api/likes', (req, res) => {
  const { target_type = 'collection', target_id, token } = req.body || {};
  if (!target_id || !token) return send(res, 400, { ok: false, error: '参数不完整' });

  const user = db.prepare('SELECT * FROM users WHERE openid = ?').get(token);
  if (!user) return send(res, 401, { ok: false, error: '请先登录' });

  const existing = db.prepare('SELECT like_id FROM likes WHERE target_type = ? AND target_id = ? AND user_id = ?')
    .get(target_type, target_id, user.user_id);

  if (existing) {
    db.prepare('DELETE FROM likes WHERE like_id = ?').run(existing.like_id);
    send(res, 200, { ok: true, data: { liked: false } });
  } else {
    db.prepare('INSERT INTO likes (target_type, target_id, user_id) VALUES (?, ?, ?)').run(target_type, target_id, user.user_id);
    send(res, 200, { ok: true, data: { liked: true } });
  }

  // 更新点赞数
  const cnt = db.prepare('SELECT COUNT(*) as cnt FROM likes WHERE target_type = ? AND target_id = ?').get(target_type, target_id).cnt;
  if (target_type === 'collection') {
    db.prepare('UPDATE collections SET likes = ? WHERE collection_id = ?').run(cnt, target_id);
  }
});

// 健康检查
app.get('/api/health', (req, res) => {
  send(res, 200, { ok: true, uptime: process.uptime(), db: 'ok' });
});

// ==================== HTTP Server ====================

const server = http.createServer((req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-User-Token');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    return res.end();
  }

  // 解析 body
  if (['POST', 'PUT', 'DELETE'].includes(req.method)) {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try { req.body = JSON.parse(body); } catch { req.body = {}; }
      handleRequest(req, res);
    });
  } else {
    handleRequest(req, res);
  }
});

// 解析 query string
function parseQuery(url) {
  const idx = url.indexOf('?');
  if (idx === -1) return {};
  const qs = url.slice(idx + 1);
  const query = {};
  for (const part of qs.split('&')) {
    const [k, v = ''] = part.split('=');
    query[decodeURIComponent(k)] = decodeURIComponent(v);
  }
  return query;
}

function handleRequest(req, res) {
  req.query = parseQuery(req.url);

  // 注入 res.json 和 res.status
  res.json = (data) => send(res, 200, data);
  res.status = (code) => ({ json: (data) => send(res, code, data) });

  const match = matchRoute(req.method, req.url);

  if (!match) {
    // 尝试静态文件
    if (req.method === 'GET') {
      return serveStatic(req, res);
    }
    return send(res, 404, { ok: false, error: 'Not Found' });
  }

  // 注入 req.params（给需要路径参数的 handler）
  const origParams = req.params;
  req.params = match.params;
  match.handler(req, res);
  req.params = origParams;
}

// 静态文件服务
const fs = require('fs');
const path = require('path');
const WWW = path.join(__dirname, '..', 'www');

function serveStatic(req, res) {
  let filePath = req.url.split('?')[0];
  if (filePath === '/') filePath = '/index.html';
  // 默认走 dataset 页
  if (filePath === '/dataset' || filePath === '/dataset/') filePath = '/dataset/index.html';
  if (filePath === '/label' || filePath === '/label/') filePath = '/label/index.html';
  
  const fullPath = path.join(WWW, filePath);
  
  // 安全检查：防止目录穿越
  if (!fullPath.startsWith(WWW)) {
    return send(res, 403, { ok: false, error: 'Forbidden' });
  }
  
  try {
    const stat = fs.statSync(fullPath);
    if (stat.isFile()) {
      const ext = path.extname(fullPath).toLowerCase();
      const mime = {
        '.html': 'text/html; charset=utf-8',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
      }[ext] || 'application/octet-stream';
      
      res.writeHead(200, { 'Content-Type': mime });
      res.end(fs.readFileSync(fullPath));
    } else {
      send(res, 404, { ok: false, error: 'Not Found' });
    }
  } catch {
    send(res, 404, { ok: false, error: 'Not Found' });
  }
}

function send(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data));
}

server.listen(PORT, () => {
  console.log(`🐢 滴个龟龟 API 已启动 → http://localhost:${PORT}`);
  console.log(`   数据库: ${db.name}`);
});
