// 滴个龟龟 集中配置
// 敏感值优先从环境变量读取，有默认值作为开发兜底

module.exports = {
  // 管理密钥 — 环境变量 ADMIN_KEY 或默认值
  adminKey: process.env.ADMIN_KEY || 'turtle-admin-2026',

  // 数据库路径
  dbPath: process.env.DB_PATH || require('path').join(__dirname, '..', 'data', 'digeguigui.db'),
};
