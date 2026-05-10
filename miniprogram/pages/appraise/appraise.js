const app = getApp();
Page({
  data: { list: [], page: 1 },
  onLoad() { this.loadData(); },
  onPullDownRefresh() { this.setData({page:1,list:[]}); this.loadData(); wx.stopPullDownRefresh(); },
  onReachBottom() { this.loadData(); },
  async loadData() {
    try {
      const data = await app.request('/api/collections', {data:{page:this.data.page,limit:12,sort:'popular'}});
      this.setData({ list: [...this.data.list,...data.list], page: this.data.page+1 });
    } catch {}
  },
  goDetail(e) { wx.navigateTo({url:'/pages/collection-detail/collection-detail?id='+e.currentTarget.dataset.id}); },
  goUpload() { wx.navigateTo({url:'/pages/upload/upload'}); }
});
