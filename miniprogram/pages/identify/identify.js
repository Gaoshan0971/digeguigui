// pages/identify/identify.js
const app = getApp();

Page({
  data: {
    previewUrl: '',
    loading: false,
    error: '',
    result: null,
    cameraReady: false,
    shareImageUrl: '',
    // 反馈闭环
    feedbackDone: false,
    feedbackIcon: '',
    feedbackMsg: '',
    showPicker: false,
    correctionCandidates: []
  },

  onReady() {
    this.ctx = wx.createCameraContext();
  },

  onCameraError() {
    this.setData({ cameraReady: false });
  },

  // 拍照
  takePhoto() {
    if (!this.ctx) return;
    this.ctx.takePhoto({
      quality: 'high',
      success: res => {
        this.setData({ previewUrl: res.tempImagePath, error: '' });
      },
      fail: () => {
        wx.showToast({ title: '拍照失败，请重试', icon: 'none' });
      }
    });
  },

  // 从相册选择
  choosePhoto() {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album'],
      success: res => {
        this.setData({ previewUrl: res.tempFilePaths[0], error: '' });
      }
    });
  },

  // 重拍
  retake() {
    this.setData({
      previewUrl: '', result: null, error: '',
      feedbackDone: false, feedbackIcon: '', feedbackMsg: '',
      showPicker: false, correctionCandidates: []
    });
  },

  // 识别
  async identify() {
    if (!this.data.previewUrl) return;

    this.setData({ loading: true, error: '', result: null });

    try {
      // 图片转 base64
      const base64 = await this.toBase64(this.data.previewUrl);

      const data = await app.request('/api/identify', {
        method: 'POST',
        data: { image_base64: base64 }
      });

      // 格式化结果
      if (data.species) {
        data.difficultyStars = '⭐'.repeat(data.species.difficulty || 1);
        if (data.species.care_params) {
          const care = typeof data.species.care_params === 'string'
            ? JSON.parse(data.species.care_params) : data.species.care_params;
          data.careParams = Object.entries(care).map(([k, v]) => ({ label: k, value: v }));
        }
      }

      this.setData({ result: data, loading: false });
      wx.hideLoading();

      // 保存原始图片用于生成分享卡
      this._lastBase64 = base64;
      this.buildShareCard();
    } catch (e) {
      this.setData({
        error: typeof e === 'string' ? e : '识别失败，请确保照片清晰',
        loading: false
      });
    }
  },

  // 图片转 base64
  toBase64(path) {
    return new Promise((resolve, reject) => {
      wx.getFileSystemManager().readFile({
        filePath: path,
        encoding: 'base64',
        success: res => resolve('data:image/jpeg;base64,' + res.data),
        fail: reject
      });
    });
  },

  // 查看饲养指南
  viewDetail() {
    if (this.data.result && this.data.result.species) {
      wx.navigateTo({
        url: '/pages/species-detail/species-detail?id=' + this.data.result.species.species_id
      });
    }
  },

  // ========== 反馈闭环 ==========

  // 确认：就是它
  async confirmResult() {
    await this.submitFeedback('confirmed');
    this.setData({
      feedbackDone: true,
      feedbackIcon: '✅',
      feedbackMsg: '已确认！训练数据+1，感谢反馈'
    });
  },

  // 纠错：弹出品种选择器
  showCorrectionPicker() {
    const candidates = (this.data.result && this.data.result.candidates) || [];
    // 优先展示候选人列表，去重
    const seen = new Set();
    const list = [];
    for (const c of candidates) {
      if (c.species_id && !seen.has(c.species_id)) {
        seen.add(c.species_id);
        list.push({ species_id: c.species_id, name_cn: c.name_cn, name_latin: c.name_latin || '' });
      }
    }
    this.setData({ showPicker: true, correctionCandidates: list });
  },

  // 选择正确品种后提交
  async correctResult(e) {
    const { id, name } = e.currentTarget.dataset;
    await this.submitFeedback('corrected', parseInt(id));
    this.setData({
      showPicker: false,
      feedbackDone: true,
      feedbackIcon: '👍',
      feedbackMsg: '已纠错为「' + name + '」，训练数据+1'
    });
  },

  // 都不对
  async rejectResult() {
    await this.submitFeedback('rejected');
    this.setData({
      feedbackDone: true,
      feedbackIcon: '📝',
      feedbackMsg: '已标记，后续会补全品种'
    });
  },

  cancelPicker() {
    this.setData({ showPicker: false });
  },

  // 搜索更多品种
  searchSpecies() {
    wx.navigateTo({ url: '/pages/gene/gene?mode=select' });
  },

  // 提交反馈到后端
  async submitFeedback(feedback_type, user_species_id) {
    const r = this.data.result;
    if (!r) return;
    try {
      await app.request('/api/identify/feedback', {
        method: 'POST',
        data: {
          image_base64: this._lastBase64 || '',
          model_species_id: r.species ? r.species.species_id : null,
          model_confidence: r.species ? (r.species.ai_confidence || 0) : 0,
          model_top3: (r.candidates || []).slice(0, 3).map(c => ({
            name_cn: c.name_cn, confidence: c.confidence, species_id: c.species_id
          })),
          engine: r.engine || '',
          feedback_type,
          user_species_id: user_species_id || null,
          token: app.globalData.token || ''
        }
      });
    } catch (e) {
      console.log('反馈提交失败:', e);
    }
  },

  // 生成分享卡（识别成功后调用）
  async buildShareCard() {
    const r = this.data.result;
    if (!r || !r.species) return;
    try {
      const data = await app.request('/api/identify/share-card', {
        method: 'POST',
        data: {
          image_base64: this._lastBase64,
          species_name: r.species.name_cn,
          confidence: r.species.ai_confidence || 0,
          engine: r.engine || '',
          difficulty: r.difficultyStars || '',
          family: r.species.family || ''
        }
      });
      this.setData({ shareImageUrl: app.globalData.API + data.image_url });
    } catch (e) {
      console.log('分享卡生成失败:', e);
    }
  },

  // 上户口 / 领证
  goProvenance() {
    const s = this.data.result && this.data.result.species;
    if (!s) return;
    wx.navigateTo({
      url: '/pages/upload/upload?species_id=' + s.species_id + '&species_name=' + s.name_cn + '&intent=provenance'
    });
  },

  // 分享
  onShareAppMessage() {
    const s = this.data.result && this.data.result.species;
    const title = s ? `我用滴个龟龟识别了一只${s.name_cn}！🐢` : '滴个龟龟 - 拍照识龟';
    const shareData = {
      title,
      path: '/pages/identify/identify'
    };
    if (this.data.shareImageUrl) {
      shareData.imageUrl = this.data.shareImageUrl;
    }
    return shareData;
  }
});
