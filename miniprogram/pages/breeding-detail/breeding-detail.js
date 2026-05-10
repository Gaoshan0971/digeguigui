const app = getApp();
Page({
  data: {},
  onLoad(opts) {
    app.request('/api/breedings/'+opts.id+'/pedigree').then(data => this.setData({breeding:data}));
  }
});
