const app = getApp();
Page({
  data: {
    imgUrl: '', speciesList: [], speciesId: '', speciesName: '',
    caption: '', city: '', intent: '',
    shareImageUrl: '', submitted: false, anchorId: '', remainingFree: null,
    showInviteCode: false, inviteCode: '', inviteVerified: false, inviteError: ''
  },
  onLoad(opt) {
    if (opt.species_id) this.setData({ speciesId: opt.species_id });
    if (opt.species_name) this.setData({ speciesName: opt.species_name });
    if (opt.intent) this.setData({ intent: opt.intent });
    // 从领码页跳转过来，自动填入邀请码
    if (opt.invite_code) {
      this.setData({
        inviteCode: opt.invite_code,
        inviteVerified: true,
        intent: 'provenance',
        showInviteCode: true
      });
    }
    app.request('/api/species', {data:{limit:50}}).then(data => this.setData({speciesList:data.list}));
  },
  chooseImage() {
    wx.chooseImage({ count:1, sizeType:['compressed'], success: r => this.setData({imgUrl:r.tempFilePaths[0]}) });
  },
  onSpeciesChange(e) { this.setData({speciesId:this.data.speciesList[e.detail.value].species_id}); },

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
    wx.showLoading({title:'锚定中…'});
    const base64 = await new Promise((res,rej) => {
      wx.getFileSystemManager().readFile({filePath:this.data.imgUrl,encoding:'base64',success:r=>res('data:image/jpeg;base64,'+r.data),fail:rej});
    });
    try {
      const isProvenance = this.data.intent === 'provenance';
      const url = isProvenance ? '/api/provenance/register' : '/api/collections';

      const payload = isProvenance
        ? {
            species_id: this.data.speciesId,
            image_base64: base64,
            notes: this.data.caption,
            city: this.data.city,
            invite_code: (this.data.inviteVerified && this.data.inviteCode) ? this.data.inviteCode.trim().toUpperCase() : undefined
          }
        : { species_id: this.data.speciesId, image_urls: [base64], caption: this.data.caption, city: this.data.city };

      const result = await app.request(url, { method:'POST', needAuth:true, data: payload });

      wx.hideLoading();

      if (isProvenance) {
        // 显示剩余额度
        const remaining = result.remaining_free;
        const methodLabel = { breeder_credit: '繁育者免费额度', invite: '达人邀请码', paid: '已付费' }[result.payment_method] || '';
        const anchorName = result.species_name || this.data.speciesName || '龟龟';

        wx.showLoading({title:'生成分享卡'});
        try {
          const card = await app.request('/api/identify/share-card', {
            method:'POST', data: {
              image_base64: base64,
              species_name: anchorName,
              title: `滴个龟龟！给${anchorName}上了户口`,
              subtitle: `锚定号 ${result.anchor_id}`,
              footer: `出生锚定 · 龟纹AI识别 · 哈希链存证${methodLabel ? ' · ' + methodLabel : ''}`,
              brand: '滴个龟龟 · 领证溯源'
            }
          });
          this.setData({
            shareImageUrl: app.globalData.API + card.image_url,
            submitted: true,
            anchorId: result.anchor_id,
            remainingFree: remaining
          });
        } catch {
          this.setData({ submitted: true, anchorId: result.anchor_id, remainingFree: remaining });
        }
        wx.hideLoading();
      } else {
        wx.showToast({ title: '发布成功' });
        setTimeout(() => wx.navigateBack(), 1500);
      }
    } catch(e) {
      wx.hideLoading();
      // 402 = 需要付费
      if (e && e.need_payment) {
        wx.showModal({
          title: '免费额度已用完',
          content: e.error || '请使用邀请码或购买锚定包 ¥19.90',
          confirmText: '知道了',
          showCancel: false
        });
      } else {
        wx.showToast({title:'上传失败',icon:'none'});
      }
    }
  },

  onShareAppMessage() {
    const name = this.data.speciesName || '龟龟';
    const shareData = {
      title: `滴个龟龟！刚给我的${name}上了户口，这颜值你们能给打几分？`,
      path: '/pages/identify/identify'
    };
    if (this.data.shareImageUrl) {
      shareData.imageUrl = this.data.shareImageUrl;
    }
    return shareData;
  },

  backHome() {
    wx.switchTab({ url: '/pages/identify/identify' });
  }
});
