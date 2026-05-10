const app = getApp();
Page({
  data: { item: null, comment: '', appraisals: [] },
  onLoad(opts) {
    app.request('/api/collections/'+opts.id).then(data => {
      this.setData({ item: data, appraisals: data.appraisals || [] });
    });
  },
  onLike() {
    const token = wx.getStorageSync('token');
    if(!token) return wx.showToast({title:'请先登录',icon:'none'});
    wx.request({ url: app.globalData.API+'/api/likes', method:'POST',
      data:{target_type:'collection', target_id:this.data.item.collection_id, token},
      success: r => { if(r.data.ok) { const item=this.data.item; item.likes+=r.data.data.liked?1:-1; this.setData({item}); } }
    });
  },
  submitAppraisal() {
    const token = wx.getStorageSync('token');
    if(!token||!this.data.comment) return;
    app.request('/api/appraisals', { method:'POST', needAuth:true,
      data:{collection_id:this.data.item.collection_id, comment:this.data.comment}
    }).then(() => { this.setData({comment:''}); wx.showToast({title:'鉴赏已提交'}); });
  },
  onInput(e) { this.setData({comment:e.detail.value}); }
});
