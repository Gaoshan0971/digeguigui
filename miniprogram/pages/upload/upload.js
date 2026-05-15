const app = getApp();
Page({
  data: {
    imgUrl: '', speciesList: [], speciesId: '', speciesName: '',
    caption: '', city: '', intent: '',
    shareImageUrl: '', submitted: false, anchorId: '', remainingFree: null,
    showInviteCode: false, inviteCode: '', inviteVerified: false, inviteError: '',
    // 批量模式
    batchMode: false, batchAnchors: [], batchCount: 0, batchDone: false
  },
  onLoad(opt) {
    if (opt.species_id) this.setData({ speciesId: opt.species_id });
    if (opt.species_name) this.setData({ speciesName: opt.species_name });
    if (opt.intent) this.setData({ intent: opt.intent });
    if (opt.invite_code) {
      this.setData({
        inviteCode: opt.invite_code, inviteVerified: true,
        intent: 'provenance', showInviteCode: true
      });
    }
    app.request('/api/species', {data:{limit:50}}).then(data => this.setData({speciesList:data.list}));
  },
  chooseImage() {
    wx.chooseImage({ count:1, sizeType:['compressed'], success: r => this.setData({imgUrl:r.tempFilePaths[0]}) });
  },
  onSpeciesChange(e) { this.setData({speciesId:this.data.speciesList[e.detail.value].species_id}); },

  toggleBatch() {
    this.setData({ 
      batchMode: !this.data.batchMode, 
      batchAnchors: [], 
      batchCount: 0, 
      batchDone: false,
      imgUrl: ''
    });
  },

  toggleInviteCode() {
    this.setData({ showInviteCode: !this.data.showInviteCode, inviteError: '' });
  },

  async verifyInviteCode() {
    const code = this.data.inviteCode.trim().toUpperCase();
    if (code.length !== 9) return;
    try {
      const data = await app.request('/api/provenance/redeem-check', {
        method:'POST', data: { code }
      });
      if (data.valid) {
        this.setData({ inviteVerified: true, inviteError: '' });
      } else {
        this.setData({ inviteVerified: false, inviteError: data.error || '邀请码无效' });
      }
    } catch (e) {
      this.setData({ inviteVerified: false, inviteError: '验证失败，请重试' });
    }
  },

  async submit() {
    if(!this.data.imgUrl||!this.data.speciesId) return wx.showToast({title:'请选择图片和品种',icon:'none'});

    // 批量模式：单独登记逻辑
    if (this.data.batchMode && this.data.intent === 'provenance') {
      return this.registerOne();
    }

    wx.showLoading({title:'锚定中…'});
    const base64 = await this.toBase64();
    try {
      const result = await this.doRegister(base64);
      wx.hideLoading();
      this.showResult(result, base64);
    } catch(e) {
      wx.hideLoading();
      this.handleError(e);
    }
  },

  // 批量模式：登记单只
  async registerOne() {
    const idx = this.data.batchCount + 1;
    wx.showLoading({title:`登记第${idx}只…`});
    const base64 = await this.toBase64();
    try {
      const result = await this.doRegister(base64);
      wx.hideLoading();
      const anchors = [...this.data.batchAnchors, {
        anchor_id: result.anchor_id,
        species_name: result.species_name,
        index: idx
      }];
      this.setData({
        imgUrl: '',
        batchAnchors: anchors,
        batchCount: idx,
        remainingFree: result.remaining_free
      });
      wx.showToast({title: `✓ 第${idx}只已登记`, icon: 'success', duration: 1200});
    } catch(e) {
      wx.hideLoading();
      this.handleError(e);
    }
  },

  // 完成批量登记
  finishBatch() {
    if (this.data.batchCount === 0) {
      return wx.showToast({title: '请先登记至少一只', icon: 'none'});
    }
    const anchors = this.data.batchAnchors;
    const name = this.data.speciesName || '龟龟';
    // 生成汇总分享卡（用最后一只的图片）
    this.setData({
      batchDone: true,
      submitted: true,
      anchorId: anchors.map(a => a.anchor_id).join(', '),
      shareImageUrl: '' // 批量模式不生成分享卡，太慢
    });
  },

  // === 共享方法 ===
  toBase64() {
    return new Promise((res,rej) => {
      wx.getFileSystemManager().readFile({
        filePath: this.data.imgUrl, encoding: 'base64',
        success: r => res('data:image/jpeg;base64,' + r.data),
        fail: rej
      });
    });
  },

  async doRegister(base64) {
    const payload = {
      species_id: this.data.speciesId,
      image_base64: base64,
      notes: this.data.caption,
      city: this.data.city,
      invite_code: (this.data.inviteVerified && this.data.inviteCode) ? this.data.inviteCode.trim().toUpperCase() : undefined
    };
    const result = await app.request('/api/provenance/register', {
      method: 'POST', needAuth: true, data: payload
    });
    return result;
  },

  showResult(result, base64) {
    const remaining = result.remaining_free;
    const methodLabel = { breeder_credit: '繁育者免费额度', invite: '达人邀请码', paid: '已付费' }[result.payment_method] || '';
    const anchorName = result.species_name || this.data.speciesName || '龟龟';

    wx.showLoading({title:'生成分享卡'});
    const setResult = (shareUrl) => {
      this.setData({
        shareImageUrl: shareUrl || '',
        submitted: true,
        anchorId: result.anchor_id,
        remainingFree: remaining
      });
    };
    app.request('/api/identify/share-card', {
      method:'POST', data: {
        image_base64: base64,
        species_name: anchorName,
        title: `滴个龟龟！给${anchorName}上了户口`,
        subtitle: `锚定号 ${result.anchor_id}`,
        footer: `出生锚定 · 龟纹AI识别 · 哈希链存证${methodLabel ? ' · ' + methodLabel : ''}`,
        brand: '滴个龟龟 · 领证溯源'
      }
    }).then(card => {
      setResult(app.globalData.API + card.image_url);
    }).catch(() => {
      setResult('');
    }).finally(() => wx.hideLoading());
  },

  handleError(e) {
    if (e && e.need_payment) {
      wx.showModal({
        title: '免费额度已用完',
        content: e.error || '请使用邀请码或购买锚定包 ¥19.90',
        confirmText: '知道了', showCancel: false
      });
    } else {
      wx.showToast({title:'登记失败,请重试',icon:'none'});
    }
  },

  onShareAppMessage() {
    const name = this.data.speciesName || '龟龟';
    const batchInfo = this.data.batchMode && this.data.batchCount > 0
      ? `，一窝${this.data.batchCount}只全部上户口！`
      : '，这颜值你们能给打几分？';
    return {
      title: `滴个龟龟！刚给${name}上了户口${batchInfo}`,
      path: '/pages/identify/identify',
      imageUrl: this.data.shareImageUrl || ''
    };
  },

  backHome() {
    wx.switchTab({ url: '/pages/identify/identify' });
  }
});
