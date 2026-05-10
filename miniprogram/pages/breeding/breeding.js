const app = getApp();
Page({
  data: { list: [] },
  onLoad() { this.loadData(); },
  async loadData() {
    try {
      const data = await app.request('/api/breedings', {data:{breeder_id:1,limit:20}});
      this.setData({list:data.list});
    } catch {}
  },
  goDetail(e) { wx.navigateTo({url:'/pages/breeding-detail/breeding-detail?id='+e.currentTarget.dataset.id}); },
  goBreeder(e) { wx.navigateTo({url:'/pages/breeder/breeder?id='+e.currentTarget.dataset.id}); }
});
