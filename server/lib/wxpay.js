// lib/wxpay.js — 微信支付 API v3 工具
// JSAPI 下单 + 回调验签 + 状态查询

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const https = require('https');

const MCHID = '1609757700';
const API_V3_KEY = 'Sixianggangyin1415926535897932ss'; // APIv3密钥
const APPID = 'wxa7aa15e29e828df8';
const SERIAL_NO = '504AF0ABAF91BE1C80AB850D39E4972F3D00FF1C'; // 证书序列号

const CERT_PATH = path.join(__dirname, '..', '..', 'DigeguiguiID', 'wxpay', 'apiclient_cert.pem');
const KEY_PATH = path.join(__dirname, '..', '..', 'DigeguiguiID', 'wxpay', 'apiclient_key.pem');

// 读商户私钥
const privKey = fs.readFileSync(KEY_PATH, 'utf-8');
const pubKey = fs.readFileSync(CERT_PATH, 'utf-8');

// ---------- 签名 ----------
function sign(method, urlPath, timestamp, nonceStr, body) {
  const message = `${method}\n${urlPath}\n${timestamp}\n${nonceStr}\n${body || ''}\n`;
  const signer = crypto.createSign('RSA-SHA256');
  signer.update(message);
  signer.end();
  return signer.sign(privKey, 'base64');
}

function makeAuthHeader(method, urlPath, body) {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const nonceStr = crypto.randomBytes(16).toString('hex');
  const signature = sign(method, urlPath, timestamp, nonceStr, body);
  return {
    'Authorization': `WECHATPAY2-SHA256-RSA2048 mchid="${MCHID}",nonce_str="${nonceStr}",timestamp="${timestamp}",serial_no="${SERIAL_NO}",signature="${signature}"`,
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'User-Agent': 'Digeguigui/1.0'
  };
}

// ---------- 回调验签 ----------
function verifyNotifySign(timestamp, nonceStr, body, signature) {
  const message = `${timestamp}\n${nonceStr}\n${body}\n`;
  const verifier = crypto.createVerify('RSA-SHA256');
  verifier.update(message);
  verifier.end();
  return verifier.verify(pubKey, signature, 'base64');
}

function decryptNotify(ciphertext, associatedData, nonce) {
  // AEAD_AES_256_GCM 解密
  const authTag = ciphertext.slice(-16);
  const data = ciphertext.slice(0, -16);
  const decipher = crypto.createDecipheriv('aes-256-gcm', Buffer.from(API_V3_KEY), Buffer.from(nonce, 'utf-8'));
  decipher.setAuthTag(Buffer.from(authTag, 'base64'));
  decipher.setAAD(Buffer.from(associatedData || '', 'utf-8'));
  const decrypted = Buffer.concat([decipher.update(Buffer.from(data, 'base64')), decipher.final()]);
  return JSON.parse(decrypted.toString('utf-8'));
}

// ---------- JSAPI 下单 ----------
function createOrder(params) {
  return new Promise((resolve, reject) => {
    const { out_trade_no, total_fee, description, openid, attach } = params;
    const body = JSON.stringify({
      appid: APPID,
      mchid: MCHID,
      description: description || '滴个龟龟服务',
      out_trade_no,
      notify_url: 'https://api.digeguigui.com/api/v2/payments/notify',
      amount: { total: total_fee, currency: 'CNY' },
      payer: { openid },
      attach: attach || ''
    });

    const urlPath = '/v3/pay/transactions/jsapi';
    const headers = makeAuthHeader('POST', urlPath, body);

    const options = {
      hostname: 'api.mch.weixin.qq.com',
      port: 443,
      path: urlPath,
      method: 'POST',
      headers,
      timeout: 10000
    };

    const req = https.request(options, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          if (result.prepay_id) {
            // 生成小程序调起支付参数
            const timestamp = Math.floor(Date.now() / 1000).toString();
            const nonceStr = crypto.randomBytes(16).toString('hex');
            const pkg = `prepay_id=${result.prepay_id}`;
            const signMsg = `${APPID}\n${timestamp}\n${nonceStr}\n${pkg}\n`;
            const paySigner = crypto.createSign('RSA-SHA256');
            paySigner.update(signMsg);
            paySigner.end();
            const paySign = paySigner.sign(privKey, 'base64');

            resolve({
              ok: true,
              data: {
                prepay_id: result.prepay_id,
                timeStamp: timestamp,
                nonceStr,
                package: pkg,
                signType: 'RSA',
                paySign
              }
            });
          } else {
            resolve({ ok: false, error: result.message || '下单失败', detail: result });
          }
        } catch (e) {
          resolve({ ok: false, error: e.message, raw: data });
        }
      });
    });

    req.on('error', e => resolve({ ok: false, error: e.message }));
    req.on('timeout', () => { req.destroy(); resolve({ ok: false, error: 'timeout' }); });
    req.write(body);
    req.end();
  });
}

module.exports = { createOrder, verifyNotifySign, decryptNotify, MCHID, APPID };
