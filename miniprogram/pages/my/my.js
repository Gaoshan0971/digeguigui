const app = getApp();
Page({
  data: { user: null },
  onShow() {
    const token = wx.getStorageSync('token');
    if (token) { this.setData({user: app.globalData.userInfo || {nickname:'龟友'}}); }
  },
  login() {
    app.login((err, user) => {
      if (err) { wx.showToast({title:'登录失败',icon:'none'}); return; }
      this.setData({user});
    });
  }
});
