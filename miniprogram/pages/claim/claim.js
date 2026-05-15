const app = getApp();

Page({
  data: {
    batchId: '',
    loading: true,
    code: '',
    alreadyClaimed: false,
    allGone: false,
    remaining: 0,
    error: ''
  },

  onLoad(opt) {
    const batchId = opt.batch_id || '';
    this.setData({ batchId });
    this.doClaim();
  },

  async doClaim() {
    this.setData({ loading: true, error: '', code: '', allGone: false });
    try {
      const token = wx.getStorageSync('token') || '';
      const data = await app.request('/api/invite-codes/claim', {
        method: 'POST',
        data: { batch_id: this.data.batchId, token }
      });
      this.setData({
        code: data.code,
        alreadyClaimed: data.already_claimed || false,
        remaining: data.remaining || 0,
        loading: false
      });
      // 存到本地，防止丢失
      if (data.code) wx.setStorageSync('claimed_code_' + this.data.batchId, data.code);
    } catch (e) {
      const err = typeof e === 'string' ? e : (e.message || '网络错误');
      if (err === '已抢完' || (e && e.all_gone)) {
        this.setData({ allGone: true, loading: false });
      } else {
        this.setData({ error: err, loading: false });
      }
    }
  },

  copyCode() {
    wx.setClipboardData({
      data: this.data.code,
      success: () => wx.showToast({ title: '已复制', icon: 'success' })
    });
  },

  goProvenance() {
    // 带上邀请码，跳转到领证页
    wx.navigateTo({
      url: '/pages/upload/upload?intent=provenance&invite_code=' + this.data.code
    });
  },

  goHome() {
    wx.switchTab({ url: '/pages/identify/identify' });
  }
});
