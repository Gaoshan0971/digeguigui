const app = getApp();
Page({
  data: { species: null, detailTab: 'info', morphs: null },
  
  onLoad(opts) {
    const id = opts.id;
    const tab = opts.tab || 'info';
    
    app.request('/api/species/' + id).then(data => {
      data.traits = typeof data.traits === 'string' ? JSON.parse(data.traits) : data.traits;
      data.care_params = typeof data.care_params === 'string' ? JSON.parse(data.care_params) : data.care_params;
      data.diffStars = '⭐'.repeat(data.difficulty || 1);
      data.morph_heavy = data.traits && data.traits.morph_heavy;
      this.setData({ species: data, detailTab: tab });
      
      if (data.morph_heavy || tab === 'morphs') {
        this.loadMorphs(id);
      }
    }).catch(() => wx.showToast({title:'加载失败',icon:'none'}));
    
    app.request('/api/species/' + id + '/collections', {data:{limit:10}}).then(data => {
      this.setData({ collections: data.list });
    }).catch(()=>{});
  },

  switchDetailTab(e) {
    this.setData({ detailTab: e.currentTarget.dataset.tab });
  },

  async loadMorphs(id) {
    try {
      const morphs = await app.request('/api/v2/species/' + id + '/morphs');
      this.setData({ morphs: morphs.data || morphs });
    } catch {}
  },

  goCollection(e) {
    wx.navigateTo({url:'/pages/collection-detail/collection-detail?id='+e.currentTarget.dataset.id});
  }
});
