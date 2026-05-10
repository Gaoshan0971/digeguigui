const app = getApp();
Page({
  data: { user: null },
  onShow() {
    const token = wx.getStorageSync('token');
    if (token) { this.loadUser(); }
  },
  login() {
    app.login((err, user) => {
      if (err) { wx.showToast({title:'登录失败',icon:'none'}); return; }
      this.setData({user});
    });
  },
  loadUser() {
    // 简化：用缓存
    this.setData({user: app.globalData.userInfo || {nickname:'龟友'}});
  }
});
