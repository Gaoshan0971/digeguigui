// routes/payments.js — 微信支付 API
// JSAPI下单 + 回调通知 + 状态查询

const crypto = require('crypto');
const { createOrder, verifyNotifySign, decryptNotify } = require('../lib/wxpay');

module.exports.register = function (app) {
  const db = require('../db');
  const { getUser } = require('../middleware/auth');

  // ==================== 下单 ====================

  // POST /api/v2/payments/order — 创建支付订单
  app.post('/api/v2/payments/order', async (req, res) => {
    const { product_type, product_id, description } = req.body || {};
    if (!product_type) return res.status(400).json({ ok: false, error: 'product_type required' });

    const user = getUser(req, res); if (!user) return;

    // 定价表
    const PRICES = {
      appraise: { fee: 990, desc: 'AI品鉴报告', limit: '次' },     // ¥9.90 = 990分
      anchor_50: { fee: 1990, desc: '出生锚定(≤50只)', limit: '窝' }, // ¥19.90
      anchor_100: { fee: 1990, desc: '出生锚定(≤100只)', limit: '窝' },
      anchor_daily: { fee: 19900, desc: '批量锚定(包天)', limit: '天' }, // ¥199
      breeder_cert: { fee: 9900, desc: '繁育者认证(年)', limit: '年' },  // ¥99
    };

    const price = PRICES[product_type];
    if (!price) return res.status(400).json({ ok: false, error: `Unknown product: ${product_type}` });

    const outTradeNo = `DGG-${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;

    const result = await createOrder({
      out_trade_no: outTradeNo,
      total_fee: price.fee,
      description: price.desc,
      openid: user.openid,
      attach: JSON.stringify({ product_type, product_id: product_id || '', user_id: user.user_id })
    });

    if (result.ok) {
      // 记录订单
      db.prepare(`INSERT INTO payment_orders (out_trade_no, user_id, product_type, product_id, total_fee, status) VALUES (?,?,?,?,?,?)`)
        .run(outTradeNo, user.user_id, product_type, product_id || '', price.fee, 'pending');
    }

    res.json(result);
  });

  // ==================== 支付回调 ====================

  // POST /api/v2/payments/notify — 微信支付异步通知
  app.post('/api/v2/payments/notify', (req, res) => {
    // 读原始 body
    let rawBody = '';
    req.on('data', chunk => rawBody += chunk);
    req.on('end', () => {
      try {
        const notify = JSON.parse(rawBody);

        // 验签
        const signature = req.headers['wechatpay-signature'];
        const timestamp = req.headers['wechatpay-timestamp'];
        const nonce = req.headers['wechatpay-nonce'];
        const serial = req.headers['wechatpay-serial'];

        if (!signature || !timestamp || !nonce) {
          return res.status(400).json({ code: 'FAIL', message: 'Missing headers' });
        }

        const valid = verifyNotifySign(timestamp, nonce, rawBody, signature);
        if (!valid) {
          console.error('[payments] Signature verification failed');
          return res.status(400).json({ code: 'FAIL', message: 'Invalid signature' });
        }

        // 解密
        const resource = notify.resource;
        const decrypted = decryptNotify(resource.ciphertext, resource.associated_data, resource.nonce);
        const outTradeNo = decrypted.out_trade_no;
        const transactionId = decrypted.transaction_id;
        const tradeState = decrypted.trade_state;

        console.log(`[payments] Notify: ${outTradeNo} → ${tradeState}`);

        if (tradeState === 'SUCCESS') {
          // 更新订单
          db.prepare('UPDATE payment_orders SET status=?, transaction_id=?, paid_at=datetime("now","localtime") WHERE out_trade_no=?')
            .run('paid', transactionId, outTradeNo);

          // 处理业务逻辑
          const order = db.prepare('SELECT * FROM payment_orders WHERE out_trade_no = ?').get(outTradeNo);
          if (order) {
            handlePaidOrder(db, order);
          }
        }

        res.status(200).json({ code: 'SUCCESS', message: 'OK' });
      } catch (e) {
        console.error('[payments] Notify error:', e.message);
        res.status(500).json({ code: 'FAIL', message: e.message });
      }
    });
  });

  // ==================== 查询 ====================

  // GET /api/v2/payments/status/:out_trade_no
  app.get('/api/v2/payments/status/:out_trade_no', (req, res) => {
    const user = getUser(req, res); if (!user) return;
    const order = db.prepare('SELECT out_trade_no, product_type, product_id, total_fee, status, paid_at FROM payment_orders WHERE out_trade_no = ? AND user_id = ?')
      .get(req.params.out_trade_no, user.user_id);
    if (!order) return res.status(404).json({ ok: false, error: 'Order not found' });
    res.json({ ok: true, data: order });
  });

  console.log('[payments] Routes registered');
};

// ---------- 支付成功后业务处理 ----------
function handlePaidOrder(db, order) {
  const { product_type, product_id, user_id } = order;

  switch (product_type) {
    case 'appraise':
      // 标记用户已有品鉴权限（下次请求 AI品鉴时检查）
      db.prepare('UPDATE users SET last_paid_appraise = datetime("now","localtime") WHERE user_id = ?').run(user_id);
      console.log(`[payments] User ${user_id} paid for appraise`);
      break;

    case 'anchor_50':
    case 'anchor_100':
    case 'anchor_daily':
      // 标记锚定额度
      db.prepare('UPDATE breeders SET cert_level = "paid" WHERE user_id = ?').run(user_id);
      console.log(`[payments] User ${user_id} paid for anchor: ${product_type}`);
      break;

    case 'breeder_cert':
      // 自动批准繁育者认证
      db.prepare('UPDATE breeders SET cert_status = "approved", cert_level = "advanced", cert_reviewed_at = datetime("now","localtime") WHERE user_id = ?').run(user_id);
      console.log(`[payments] User ${user_id} paid for breeder cert`);
      break;
  }
}
