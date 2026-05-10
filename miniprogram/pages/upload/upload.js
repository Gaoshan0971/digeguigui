const app = getApp();
Page({
  data: { imgUrl: '', speciesList: [], speciesId: '', caption: '', city: '' },
  onLoad() {
    app.request('/api/species', {data:{limit:50}}).then(data => this.setData({speciesList:data.list}));
  },
  chooseImage() {
    wx.chooseImage({ count:1, sizeType:['compressed'], success: r => this.setData({imgUrl:r.tempFilePaths[0]}) });
  },
  onSpeciesChange(e) { this.setData({speciesId:this.data.speciesList[e.detail.value].species_id}); },
  async submit() {
    if(!this.data.imgUrl||!this.data.speciesId) return wx.showToast({title:'请选择图片和品种',icon:'none'});
    wx.showLoading({title:'上传中'});
    // 先上传图片到 COS (简化：直接用 base64)
    const base64 = await new Promise((res,rej) => {
      wx.getFileSystemManager().readFile({filePath:this.data.imgUrl,encoding:'base64',success:r=>res('data:image/jpeg;base64,'+r.data),fail:rej});
    });
    try {
      await app.request('/api/collections', {
        method:'POST', needAuth:true,
        data:{species_id:this.data.speciesId, image_urls:[base64], caption:this.data.caption, city:this.data.city}
      });
      wx.hideLoading(); wx.showToast({title:'发布成功'}); wx.navigateBack();
    } catch(e) {
      wx.hideLoading(); wx.showToast({title:'上传失败',icon:'none'});
    }
  }
});
