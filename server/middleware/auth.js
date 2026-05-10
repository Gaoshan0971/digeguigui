// middleware/auth.js — 认证辅助
const db = require('../db');

// 从请求中提取用户，失败则返回 null + 已发送错误响应
function getUser(req, res) {
  const token = req.headers['x-user-token'] || (req.body && req.body.token) || req.query.token;
  if (!token) {
    res.status(401).json({ ok: false, error: '请先登录' });
    return null;
  }
  const user = db.prepare('SELECT * FROM users WHERE openid = ?').get(token);
  if (!user) {
    res.status(401).json({ ok: false, error: '用户不存在' });
    return null;
  }
  return user;
}

module.exports = { getUser };
