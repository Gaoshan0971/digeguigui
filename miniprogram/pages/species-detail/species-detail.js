const app = getApp();
Page({
  data: { species: null, detailTab: 'info', morphs: null, prices: null, priceLoaded: false },
  
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
    const tab = e.currentTarget.dataset.tab;
    this.setData({ detailTab: tab });
    if (tab === 'morphs') this.loadMorphs(this.options.id);
  },

  async loadMorphs(id) {
    try {
      const [morphRes, priceRes] = await Promise.all([
        app.request('/api/v2/species/' + id + '/morphs'),
        app.request('/api/v2/prices/morphs', { data: { species_id: id } })
      ]);
      
      const morphs = morphRes.data || morphRes;
      const priceList = priceRes.list || priceRes.data || [];
      
      // Build price map
      const priceMap = {};
      for (const p of priceList) {
        const key = p.type === 'gene' ? p.symbol : p.symbol;  // symbol = gene_symbol or combo_name
        priceMap[key] = p;
      }
      
      // Attach prices to genes
      if (morphs.genes) {
        morphs.genes = morphs.genes.map(g => ({
          ...g,
          price: priceMap[g.gene_symbol] || null
        }));
      }
      
      // Attach prices to combos
      if (morphs.combos) {
        morphs.combos = morphs.combos.map(c => ({
          ...c,
          price: priceMap[c.combo_name] || null
        }));
      }
      
      // Build price ladder
      const speciesPrice = await this.loadSpeciesPrice(id);
      morphs.priceLadder = this.buildPriceLadder(speciesPrice, priceMap, morphs);
      
      this.setData({ morphs, priceLoaded: true });
    } catch {}
  },

  async loadSpeciesPrice(id) {
    try {
      const res = await app.request('/api/v2/prices/species/' + id);
      return res.data;
    } catch { return null; }
  },

  buildPriceLadder(speciesPrice, priceMap, morphs) {
    const ladder = [];
    
    // Step 1: Normal/Wild type
    if (speciesPrice) {
      ladder.push({
        label: '普通个体',
        desc: 'Wild Type',
        low: speciesPrice.normal_low,
        high: speciesPrice.normal_high,
        currency: speciesPrice.currency || 'CNY'
      });
    }
    
    // Step 2: Single genes (top 3 cheapest)
    if (morphs.genes) {
      const pricedGenes = morphs.genes
        .filter(g => g.price && g.price.price_range_low)
        .sort((a, b) => (a.price.price_range_low||0) - (b.price.price_range_low||0))
        .slice(0, 3);
      
      for (const g of pricedGenes) {
        ladder.push({
          label: g.gene_name_cn || g.gene_name,
          desc: g.gene_symbol,
          low: g.price.price_range_low,
          high: g.price.price_range_high,
          currency: 'CNY',
          rarity: g.price.rarity
        });
      }
    }
    
    // Step 3: Classic combos (top 3)
    if (morphs.combos) {
      const pricedCombos = morphs.combos
        .filter(c => c.price && c.price.price_range_low)
        .sort((a, b) => (a.price.price_range_low||0) - (b.price.price_range_low||0))
        .slice(0, 3);
      
      for (const c of pricedCombos) {
        ladder.push({
          label: c.combo_name_cn || c.combo_name,
          desc: c.combo_formula,
          low: c.price.price_range_low,
          high: c.price.price_range_high,
          currency: 'CNY',
          rarity: c.price.rarity
        });
      }
    }
    
    return ladder;
  },

  goCollection(e) {
    wx.navigateTo({url:'/pages/collection-detail/collection-detail?id='+e.currentTarget.dataset.id});
  }
});
