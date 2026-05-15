// routes/credits.js — 锚定额度购买 + 管理员授予
const crypto = require('crypto');

module.exports.register = function (app) {
  const db = require('../db');
  const { getUser } = require('../middleware/auth');

  // 产品定义
  const PRODUCTS = {
    credit_10:  { fee: 1990, anchors: 10,  name: '锚定额度包(10个)',  desc: '¥19.90 / 10锚定' },
    credit_200: { fee: 19900,anchors: 200, name: '锚定额度包(200个)', desc: '¥199 / 200锚定' },
  };

  const ADMIN_KEY = 'turtle-admin-2026';

  // ==================== 下单 ====================

  // POST /api/v2/credits/order — 创建额度购买订单
  app.post('/api/v2/credits/order', (req, res) => {
    const { product_type, count } = req.body || {};
    if (!product_type) return res.status(400).json({ ok: false, error: 'product_type required' });

    const product = PRODUCTS[product_type];
    if (!product) return res.status(400).json({ ok: false, error: `Unknown product: ${product_type}. Valid: credit_10, credit_200` });

    const user = getUser(req, res); if (!user) return;

    const qty = Math.max(1, parseInt(count) || 1);
    const outTradeNo = `CREDIT-${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;
    const totalFee = product.fee * qty;
    const totalAnchors = product.anchors * qty;

    // 记录订单（暂未接入支付，状态 pending）
    db.prepare(`INSERT INTO payment_orders (out_trade_no, user_id, product_type, product_id, total_fee, status)
      VALUES (?,?,?,?,?,?)`)
      .run(outTradeNo, user.user_id, product_type, String(qty), totalFee, 'pending');

    res.json({
      ok: true,
      data: {
        order_id: outTradeNo,
        amount: totalFee,
        amount_yuan: (totalFee / 100).toFixed(2),
        product_name: product.name,
        quantity: qty,
        anchors: totalAnchors,
      }
    });
  });

  // ==================== 管理员授予额度 ====================

  // POST /api/admin/credits/grant — 管理员直接授予锚定额度
  app.post('/api/admin/credits/grant', (req, res) => {
    const { admin_key, user_id, amount } = req.body || {};

    // 验证 admin key
    if (admin_key !== ADMIN_KEY) {
      return res.status(403).json({ ok: false, error: 'Invalid admin key' });
    }

    // 验证参数
    if (!user_id || !amount) {
      return res.status(400).json({ ok: false, error: 'user_id and amount required' });
    }

    const grantAmount = parseInt(amount);
    if (![10, 200].includes(grantAmount)) {
      return res.status(400).json({ ok: false, error: 'amount must be 10 or 200' });
    }

    // 查找 breeder 记录
    const breeder = db.prepare('SELECT * FROM breeders WHERE user_id = ?').get(user_id);
    if (!breeder) {
      return res.status(404).json({ ok: false, error: 'Breeder not found for this user_id' });
    }

    // 增加额度
    const newBalance = breeder.free_anchors + grantAmount;
    db.prepare("UPDATE breeders SET free_anchors = ?, updated_at = datetime('now','localtime') WHERE id = ?")
      .run(newBalance, breeder.id);

    console.log(`[credits] Admin granted ${grantAmount} anchors to user ${user_id}. Balance: ${breeder.free_anchors} → ${newBalance}`);

    res.json({
      ok: true,
      data: {
        user_id: parseInt(user_id),
        new_balance: newBalance,
        granted: grantAmount,
      }
    });
  });

  console.log('[credits] Routes registered');
};
