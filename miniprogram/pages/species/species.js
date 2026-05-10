// pages/species/species.js
const app = getApp();

Page({
  data: {
    list: [],
    loading: true
  },

  onLoad() {
    this.loadSpecies();
  },

  onShow() {
    if (!this.data.list.length) this.loadSpecies();
  },

  async loadSpecies() {
    try {
      const data = await app.request('/api/species', { data: { limit: 50 } });
      this.setData({ list: data.list, loading: false });
    } catch {
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/pages/species-detail/species-detail?id=' + id });
  },

  onSearch(e) {
    const kw = e.detail.value;
    if (!kw) { this.loadSpecies(); return; }
    app.request('/api/species', { data: { keyword: kw } })
      .then(data => this.setData({ list: data.list }))
      .catch(() => {});
  }
});
