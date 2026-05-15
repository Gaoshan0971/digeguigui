const app = getApp();
Page({
  data: {
    imgUrl: '', speciesList: [], speciesId: '', speciesName: '',
    caption: '', city: '', intent: '',
    shareImageUrl: '', submitted: false
  },
  onLoad(opt) {
    if (opt.species_id) this.setData({ speciesId: opt.species_id });
    if (opt.species_name) this.setData({ speciesName: opt.species_name });
    if (opt.intent) this.setData({ intent: opt.intent });
    app.request('/api/species', {data:{limit:50}}).then(data => this.setData({speciesList:data.list}));
  },
  chooseImage() {
    wx.chooseImage({ count:1, sizeType:['compressed'], success: r => this.setData({imgUrl:r.tempFilePaths[0]}) });
  },
  onSpeciesChange(e) { this.setData({speciesId:this.data.speciesList[e.detail.value].species_id}); },
  async submit() {
    if(!this.data.imgUrl||!this.data.speciesId) return wx.showToast({title:'请选择图片和品种',icon:'none'});
    wx.showLoading({title:'上传中'});
    const base64 = await new Promise((res,rej) => {
      wx.getFileSystemManager().readFile({filePath:this.data.imgUrl,encoding:'base64',success:r=>res('data:image/jpeg;base64,'+r.data),fail:rej});
    });
    try {
      const isProvenance = this.data.intent === 'provenance';
      const url = isProvenance ? '/api/provenance/register' : '/api/collections';
      await app.request(url, {
        method:'POST', needAuth:true,
        data: isProvenance
          ? { species_id: this.data.speciesId, image_base64: base64, notes: this.data.caption, city: this.data.city }
          : { species_id: this.data.speciesId, image_urls: [base64], caption: this.data.caption, city: this.data.city }
      });
      wx.hideLoading();

      if (isProvenance) {
        // 生成领证分享卡
        wx.showLoading({title:'生成分享卡'});
        try {
          const name = this.data.speciesName || '龟龟';
          const card = await app.request('/api/identify/share-card', {
            method:'POST', data: {
              image_base64: base64,
              species_name: name,
              title: `滴个龟龟！刚给我的${name}上了户口`,
              subtitle: '这颜值你们能给打几分？',
              footer: '出生锚定 · 龟纹AI识别 · 哈希链存证',
              brand: '滴个龟龟 · 领证溯源'
            }
          });
          this.setData({
            shareImageUrl: app.globalData.API + card.image_url,
            submitted: true
          });
        } catch {}
        wx.hideLoading();
      } else {
        wx.showToast({ title: '发布成功' });
        setTimeout(() => wx.navigateBack(), 1500);
      }
    } catch(e) {
      wx.hideLoading(); wx.showToast({title:'上传失败',icon:'none'});
    }
  },

  // 分享
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
