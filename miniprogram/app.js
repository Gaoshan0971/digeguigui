// app.js — 滴个龟龟 小程序入口
const API = 'https://api.digeguigui.com';

App({
  globalData: {
    userInfo: null,
    token: null,
    API: API
  },

  onLaunch() {
    // 检查登录状态
    const token = wx.getStorageSync('token');
    if (token) {
      this.globalData.token = token;
    }
  },

  // 登录 / 自动注册
  login(cb) {
    wx.login({
      success: res => {
        if (res.code) {
          wx.request({
            url: API + '/api/users/login',
            method: 'POST',
            data: { openid: res.code, nickname: '' },
            success: resp => {
              if (resp.data.ok) {
                const token = resp.data.data.token;
                this.globalData.token = token;
                this.globalData.userInfo = resp.data.data.user;
                wx.setStorageSync('token', token);
                cb && cb(null, resp.data.data.user);
              } else {
                cb && cb(resp.data.error);
              }
            },
            fail: err => cb && cb(err)
          });
        }
      }
    });
  },

  // 通用请求
  request(url, options = {}) {
    const { method = 'GET', data, needAuth = false } = options;
    const header = { 'Content-Type': 'application/json' };
    if (needAuth && this.globalData.token) {
      header['X-User-Token'] = this.globalData.token;
    }
    return new Promise((resolve, reject) => {
      wx.request({
        url: API + url,
        method,
        data,
        header,
        success: res => {
          if (res.statusCode === 200 && res.data.ok) {
            resolve(res.data.data);
          } else {
            reject(res.data.error || '请求失败');
          }
        },
        fail: err => reject(err)
      });
    });
  }
});
