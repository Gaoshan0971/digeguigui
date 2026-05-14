// pages/gene/gene.js
const app = getApp();

Page({
  data: {
    tab: 'species',
    curCat: '',
    speciesList: [],
    morphSpecies: [],
    breedingList: [],
    loading: true
  },

  onShow() {
    this.loadSpecies();
    this.loadMorphSpecies();
    this.loadBreedings();
  },

  switchTab(e) { this.setData({ tab: e.currentTarget.dataset.tab }); },
  setCat(e) { this.setData({ curCat: e.currentTarget.dataset.cat }); this.loadSpecies(); },

  async loadSpecies() {
    this.setData({ loading: true });
    try {
      const params = { limit: 50 };
      if (this.data.curCat) params.category = this.data.curCat;
      const data = await app.request('/api/v2/species', { data: params });
      // Add morph_heavy flag
      const list = (data.list||[]).map(s => ({
        ...s,
        morph_heavy: s.traits && JSON.parse(s.traits||'{}').morph_heavy
      }));
      this.setData({ speciesList: list, loading: false });
    } catch {
      this.setData({ loading: false });
    }
  },

  async loadMorphSpecies() {
    try {
      const heavy = await app.request('/api/v2/morphs/heavy');
      const species = [];
      for (const s of (heavy.list || []).slice(0, 6)) {
        // Get morphs with preview
        try {
          const morphs = await app.request('/api/v2/species/' + s.species_id + '/morphs');
          species.push({
            ...s,
            genes_preview: (morphs.genes || []).slice(0, 5).map(g => ({
              gene_symbol: g.gene_symbol,
              gene_name: g.gene_name,
              gene_name_cn: g.gene_name_cn,
              inheritance: g.inheritance
            })),
            combos_preview: (morphs.combos || []).slice(0, 4)
          });
        } catch {
          species.push(s);
        }
      }
      this.setData({ morphSpecies: species });
    } catch {}
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
    app.request('/api/v2/species', { data: { q: kw } })
      .then(data => this.setData({ speciesList: data.list }))
      .catch(() => {});
  },

  goSpecies(e) {
    wx.navigateTo({ url: '/pages/species-detail/species-detail?id=' + e.currentTarget.dataset.id });
  },

  goMorphDetail(e) {
    const id = e.currentTarget.dataset.id;
    const name = e.currentTarget.dataset.name;
    // Navigate to species-detail with morph tab active
    wx.navigateTo({ url: '/pages/species-detail/species-detail?id=' + id + '&tab=morphs' });
  },

  goBreeding(e) {
    wx.navigateTo({ url: '/pages/breeding-detail/breeding-detail?id=' + e.currentTarget.dataset.id });
  },

  goMorphId() {
    wx.navigateTo({ url: '/pages/morph-id/morph-id' });
  }
});
