const app = getApp();

Page({
  data: {
    batchId: '',
    isHost: false,
    loading: true,
    code: '',
    alreadyClaimed: false,
    allGone: false,
    remaining: 0,
    error: '',
    // host mode fields
    shareCardUrl: '',
    total: 0,
    used: 0,
    createdBy: ''
  },

  onLoad(opt) {
    const batchId = opt.batch_id || '';
    const isHost = opt.role === 'host';
    this.setData({ batchId, isHost });

    if (isHost) {
      this.loadBatchInfo();
    } else {
      this.doClaim();
    }
  },

  // ── 达人模式：加载批次信息 ──
  async loadBatchInfo() {
    this.setData({ loading: true });
    try {
      const data = await app.request('/api/invite-codes/batch/' + this.data.batchId);
      this.setData({
        total: data.total,
        used: data.used,
        remaining: data.remaining,
        allGone: data.all_gone,
        shareCardUrl: data.share_card_url ? app.globalData.API + data.share_card_url : '',
        createdBy: data.created_by || '',
        loading: false
      });
    } catch (e) {
      this.setData({ error: '加载失败', loading: false });
    }
  },

  // ── 用户模式：自动领码 ──
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
    wx.navigateTo({
      url: '/pages/upload/upload?intent=provenance&invite_code=' + this.data.code
    });
  },

  goHome() {
    wx.switchTab({ url: '/pages/identify/identify' });
  },

  // ── 分享（达人模式） ──
  onShareAppMessage() {
    if (!this.data.isHost) return {};
    return {
      title: '滴个龟龟！可以给自己的爬宠上户口了，十个爬宠身份证名额免费领取，先抢先得！',
      path: '/pages/claim/claim?batch_id=' + this.data.batchId,
      imageUrl: this.data.shareCardUrl || ''
    };
  }
});
