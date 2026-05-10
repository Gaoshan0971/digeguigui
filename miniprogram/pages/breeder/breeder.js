const app = getApp();
Page({
  data: {},
  onLoad(opts) {
    app.request('/api/breeders/'+opts.id).then(data => this.setData({breeder:data}));
  }
});
