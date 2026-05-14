const app = getApp();
Page({
  data: {
    item: null,
    comment: '',
    appraisals: [],
    aiResult: null,       // AI品鉴结果
    aiLoading: false,     // AI品鉴中
    hasPaidAppraise: false // 是否已付费品鉴过
  },

  onLoad(opts) {
    this.loadDetail(opts.id);
  },

  onShow() {
    // 每次回到页面，检查支付状态
    const pendingOrder = wx.getStorageSync('pending_appraise_order');
    if (pendingOrder && this.data.item) {
      this.checkPayment(pendingOrder);
    }
  },

  async loadDetail(id) {
    try {
      const data = await app.request('/api/collections/' + id);
      const hasPaid = data.ai_appraised || false;
      const aiResult = data.ai_appraisal || null;
      this.setData({
        item: data,
        appraisals: data.appraisals || [],
        hasPaidAppraise: hasPaid,
        aiResult
      });
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  // ========== ¥9.90 AI品鉴 ==========
  async doAIAppraise() {
    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    if (this.data.aiLoading) return;

    wx.showModal({
      title: 'AI品鉴报告',
      content: '¥9.90 解锁完整品鉴报告\n五维打分 + 品级 + 市场估价',
      confirmText: '¥9.90 立即解锁',
      success: async (modalRes) => {
        if (!modalRes.confirm) return;

        this.setData({ aiLoading: true });

        try {
          // 1. 下单
          const orderRes = await app.request('/api/v2/payments/order', {
            method: 'POST',
            needAuth: true,
            data: {
              product_type: 'appraise',
              product_id: String(this.data.item.collection_id)
            }
          });

          if (!orderRes.ok) {
            wx.showToast({ title: orderRes.error || '下单失败', icon: 'none' });
            this.setData({ aiLoading: false });
            return;
          }

          // 2. 调起微信支付
          const payParams = {
            timeStamp: orderRes.data.timeStamp,
            nonceStr: orderRes.data.nonceStr,
            package: orderRes.data.package,
            signType: orderRes.data.signType,
            paySign: orderRes.data.paySign
          };

          // 暂存订单号，支付回来后检查
          wx.setStorageSync('pending_appraise_order', orderRes.data);

          wx.requestPayment({
            ...payParams,
            success: async () => {
              // 3. 支付成功 → 调AI品鉴
              wx.removeStorageSync('pending_appraise_order');
              await this.runAIAppraise();
            },
            fail: (err) => {
              wx.showToast({ title: '支付取消', icon: 'none' });
              this.setData({ aiLoading: false });
            }
          });

        } catch (e) {
          wx.showToast({ title: '下单失败', icon: 'none' });
          this.setData({ aiLoading: false });
        }
      }
    });
  },

  // 执行AI品鉴
  async runAIAppraise() {
    try {
      const result = await app.request('/api/collections/' + this.data.item.collection_id + '/appraise-ai', {
        method: 'POST',
        needAuth: true
      });

      if (result.ok) {
        this.setData({
          aiResult: result.data,
          hasPaidAppraise: true,
          aiLoading: false
        });
        wx.showToast({ title: '品鉴完成！', icon: 'success' });
      } else {
        wx.showToast({ title: result.error || '品鉴失败', icon: 'none' });
        this.setData({ aiLoading: false });
      }
    } catch (e) {
      wx.showToast({ title: '品鉴失败', icon: 'none' });
      this.setData({ aiLoading: false });
    }
  },

  onLike() {
    const token = wx.getStorageSync('token');
    if (!token) return wx.showToast({ title: '请先登录', icon: 'none' });
    wx.request({
      url: app.globalData.API + '/api/likes', method: 'POST',
      data: { target_type: 'collection', target_id: this.data.item.collection_id, token },
      success: r => {
        if (r.data.ok) {
          const item = this.data.item;
          item.likes += r.data.data.liked ? 1 : -1;
          this.setData({ item });
        }
      }
    });
  },

  submitAppraisal() {
    const token = wx.getStorageSync('token');
    if (!token || !this.data.comment) return;
    app.request('/api/appraisals', {
      method: 'POST', needAuth: true,
      data: { collection_id: this.data.item.collection_id, comment: this.data.comment }
    }).then(() => {
      this.setData({ comment: '' });
      wx.showToast({ title: '鉴赏已提交' });
    });
  },

  onInput(e) { this.setData({ comment: e.detail.value }); }
});
