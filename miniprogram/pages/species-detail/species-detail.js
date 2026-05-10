const app = getApp();
Page({
  data: { species: null },
  onLoad(opts) {
    app.request('/api/species/' + opts.id).then(data => {
      data.traits = typeof data.traits === 'string' ? JSON.parse(data.traits) : data.traits;
      data.care_params = typeof data.care_params === 'string' ? JSON.parse(data.care_params) : data.care_params;
      data.diffStars = '⭐'.repeat(data.difficulty || 1);
      this.setData({ species: data });
    }).catch(() => wx.showToast({title:'加载失败',icon:'none'}));
    // 加载该品种藏品
    app.request(`/api/species/${opts.id}/collections`, {data:{limit:10}}).then(data => {
      this.setData({ collections: data.list });
    }).catch(()=>{});
  },
  goCollection(e) {
    wx.navigateTo({url:'/pages/collection-detail/collection-detail?id='+e.currentTarget.dataset.id});
  }
});
