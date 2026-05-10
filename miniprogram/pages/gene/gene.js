// pages/gene/gene.js
const app = getApp();

Page({
  data: {
    tab: 'species',
    speciesList: [],
    breedingList: [],
    loading: true
  },

  onShow() {
    this.loadSpecies();
    this.loadBreedings();
  },

  switchTab(e) {
    this.setData({ tab: e.currentTarget.dataset.tab });
  },

  async loadSpecies() {
    try {
      const data = await app.request('/api/species', { data: { limit: 50 } });
      this.setData({ speciesList: data.list, loading: false });
    } catch {
      this.setData({ loading: false });
    }
  },

  async loadBreedings() {
    try {
      const data = await app.request('/api/breedings', { data: { breeder_id: 1, limit: 20 } });
      this.setData({ breedingList: data.list });
    } catch {}
  },

  onSearch(e) {
    const kw = e.detail.value;
    if (!kw) { this.loadSpecies(); return; }
    app.request('/api/species', { data: { keyword: kw } })
      .then(data => this.setData({ speciesList: data.list }))
      .catch(() => {});
  },

  goSpecies(e) {
    wx.navigateTo({ url: '/pages/species-detail/species-detail?id=' + e.currentTarget.dataset.id });
  },

  goBreeding(e) {
    wx.navigateTo({ url: '/pages/breeding-detail/breeding-detail?id=' + e.currentTarget.dataset.id });
  }
});
