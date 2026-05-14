// pages/morph-id/morph-id.js
const app = getApp();

// Question bank: species → [questions]
const QUESTION_BANK = {
  // 玉米蛇
  corn: [
    { q: '基础色调？', desc: '蛇的整体底色是什么样的？', opts: [
      { v:'orange', emoji:'🟠', label:'橙/红棕', d:'Normal 经典橙色' },
      { v:'white', emoji:'⚪', label:'白/粉白', d:'Amel/Snow/Blizzard 类' },
      { v:'grey', emoji:'🔘', label:'灰/银灰', d:'Anery/Charcoal/Ghost 类' },
      { v:'yellow', emoji:'🟡', label:'金黄/焦糖', d:'Caramel/Butter/Amber 类' },
      { v:'lavender', emoji:'🟣', label:'薰衣草/紫', d:'Lavender/Orchid 类' },
    ]},
    { q: '纹路样式？', desc: '背部和侧面的花纹是什么样的？', opts: [
      { v:'normal', emoji:'〰️', label:'Normal 鞍状纹', d:'标准鞍状斑' },
      { v:'motley', emoji:'⭕', label:'圆点/圆圈', d:'Motley 圆斑' },
      { v:'stripe', emoji:'▬', label:'直线/条纹', d:'Stripe 背中线' },
      { v:'diffused', emoji:'🩸', label:'血红色扩散', d:'Diffused/Bloodred 扩散纹' },
      { v:'tessera', emoji:'🔗', label:'镶嵌/网状', d:'Tessera 背纹' },
    ]},
    { q: '有无白斑？', desc: '身体上有没有纯白色区块？', opts: [
      { v:'no', emoji:'❌', label:'无白斑' },
      { v:'pied', emoji:'⬜', label:'有白斑/派', d:'Pied Sided 侧派/白斑' },
    ]},
    { q: '鳞片状态？', desc: '鳞片看起来正常还是有特殊变异？', opts: [
      { v:'normal', emoji:'✅', label:'正常鳞片' },
      { v:'scaleless', emoji:'✨', label:'无鳞/光滑', d:'Scaleless 无鳞' },
      { v:'microscale', emoji:'🔬', label:'微型鳞片', d:'Microscale' },
    ]},
    { q: '额外特征？', desc: '还有其他特殊特征吗？', opts: [
      { v:'none', emoji:'➖', label:'无特殊' },
      { v:'bright_orange', emoji:'🍊', label:'鲜艳橙色', d:'Sunkissed 日吻' },
      { v:'pink_tint', emoji:'🌸', label:'粉色调', d:'Lavender/Opal/Palmetto' },
      { v:'high_contrast', emoji:'🎨', label:'高对比度', d:'Lava/Ultra 熔岩' },
    ]},
  ],
  // 球蟒
  ball: [
    { q: '基础色调？', desc: '蛇的主要颜色？', opts: [
      { v:'normal', emoji:'🟫', label:'棕/黑 Normal', d:'标准野型' },
      { v:'yellow', emoji:'🟡', label:'黄色系', d:'Pastel/Banana/Enchi' },
      { v:'white', emoji:'⚪', label:'白/灰白', d:'BEL/Ivory/Fire' },
      { v:'orange', emoji:'🟠', label:'橙色系', d:'Orange Dream/Enchi' },
      { v:'dark', emoji:'⬛', label:'深黑/棕黑', d:'Cinnamon/GHI/Mahogany' },
    ]},
    { q: '纹路样式？', desc: '花纹特征？', opts: [
      { v:'normal', emoji:'🔹', label:'Normal 外星人头', d:'标准花纹' },
      { v:'reduced', emoji:'◽', label:'简化/褪纹', d:'Enchi/Pastel 简化' },
      { v:'stripe', emoji:'▬', label:'背中线/直线', d:'Pinstripe/Genetic Stripe' },
      { v:'spider', emoji:'🕸️', label:'蜘蛛网纹', d:'Spider 蛛网纹' },
      { v:'clown', emoji:'🤡', label:'小丑斑', d:'Clown 简斑+头纹' },
    ]},
    { q: '白色区块？', desc: '有没有纯白色块？', opts: [
      { v:'none', emoji:'➖', label:'无' },
      { v:'pied', emoji:'⬜', label:'有白块(派)', d:'Pied' },
      { v:'high_white', emoji:'🤍', label:'高白侧', d:'Calico/Sugar' },
    ]},
    { q: '眼睛颜色？', desc: '注意看眼睛', opts: [
      { v:'dark', emoji:'👁️', label:'黑/深色' },
      { v:'blue', emoji:'🔵', label:'蓝色', d:'BEL 蓝眼白化' },
      { v:'light', emoji:'🟢', label:'浅色/绿' },
      { v:'red', emoji:'🔴', label:'红色', d:'Albino' },
    ]},
    { q: '特殊标记？', desc: '有什么一眼能认出的特征？', opts: [
      { v:'none', emoji:'➖', label:'无' },
      { v:'head_stamp', emoji:'💀', label:'头纹明显', d:'Clown/Spotnose' },
      { v:'freckles', emoji:'✨', label:'雀斑/斑点', d:'Banana freckles' },
      { v:'clean_belly', emoji:'⬜', label:'干净白腹' },
    ]},
  ],
};

// Species → question set mapping
const SPECIES_QUESTIONS = {
  'Pantherophis guttatus': 'corn',
  'Python regius': 'ball',
};

// Scoring: answer → gene/combo matches
const MORPH_RULES = {
  // 玉米蛇
  corn: {
    orange: ['normal'],
    white: ['amelanistic','anerythristic','charcoal'],
    grey: ['anerythristic','charcoal','ghost'],
    yellow: ['caramel','butter','honey','amber'],
    lavender: ['lavender','orchid','plasma'],
    normal: ['normal'],
    motley: ['motley'],
    stripe: ['stripe'],
    diffused: ['diffused','granite','avalanche','pewter'],
    tessera: ['tessera'],
    pied: ['pied_sided'],
    scaleless: ['scaleless'],
    microscale: ['microscale'],
    bright_orange: ['sunkissed'],
    pink_tint: ['lavender','opal','palmetto'],
    none: ['normal'],
  },
  // 球蟒
  ball: {
    normal: ['normal'],
    yellow: ['pastel','banana','enchi','lesser'],
    white: ['mojave','lesser','fire','yellow_belly'],
    orange: ['orange_dream','enchi'],
    dark: ['cinnamon','black_pastel','ghi','mahogany'],
    reduced: ['enchi','pastel'],
    stripe: ['pinstripe','genetic_stripe'],
    spider: ['spider'],
    clown: ['clown'],
    pied: ['pied'],
    high_white: ['calico'],
    blue: ['mojave','lesser'],  // BEL
    light: ['pastel','banana'],
    red: ['albino'],
    head_stamp: ['clown','spotnose'],
    freckles: ['banana'],
    clean_belly: ['yellow_belly'],
    none: ['normal'],
  },
};

Page({
  data: {
    step: 1, selSpecies: null, speciesList: [],
    currentQ: '', currentQDesc: '', currentOptions: [],
    selAnswers: {}, answers: [],
    matches: null, loading: false, morphCount: 0
  },

  onShow() { this.loadSpecies(); },

  async loadSpecies() {
    try {
      const res = await app.request('/api/v2/morphs/heavy');
      this.setData({ speciesList: res.list || res.data || [] });
    } catch {}
  },

  pickSpecies(e) {
    this.setData({ selSpecies: parseInt(e.currentTarget.dataset.id) });
  },

  startQuestions() {
    const sp = this.data.speciesList.find(s => s.species_id === this.data.selSpecies);
    if (!sp) return;
    const qSet = SPECIES_QUESTIONS[sp.name_latin.split(' (')[0]] || 'corn';
    this.qSet = qSet;
    this.questions = QUESTION_BANK[qSet];
    this.setData({ step: 2, answers: [], selAnswers: {} });
    this.showQuestion(0);
  },

  showQuestion(idx) {
    if (idx >= this.questions.length) { this.computeMatch(); return; }
    const q = this.questions[idx];
    this.setData({
      step: idx + 2,
      currentQ: q.q, currentQDesc: q.desc,
      currentOptions: q.opts.map(o => ({ value: o.v, emoji: o.emoji, label: o.label, desc: o.d||'' }))
    });
  },

  pickAnswer(e) {
    const idx = this.data.step - 2;
    const sel = { ...this.data.selAnswers };
    sel[idx] = e.currentTarget.dataset.value;
    this.setData({ selAnswers: sel });
  },

  nextStep() {
    const idx = this.data.step - 2;
    const answers = [...this.data.answers];
    answers[idx] = this.data.selAnswers[idx];
    this.setData({ answers });
    this.showQuestion(idx + 1);
  },

  prevStep() {
    const idx = this.data.step - 3;
    if (idx < 0) { this.setData({ step: 1 }); return; }
    this.showQuestion(idx);
  },

  async computeMatch() {
    this.setData({ step: 7, loading: true });
    const sp = this.data.speciesList.find(s => s.species_id === this.data.selSpecies);
    const rules = MORPH_RULES[this.qSet] || {};
    
    // Score each gene/combo
    try {
      const morphRes = await app.request('/api/v2/species/' + this.data.selSpecies + '/morphs');
      const morphs = morphRes.data || morphRes;
      const allMorphs = [
        ...(morphs.genes||[]).map(g => ({ ...g, type:'gene', formula:g.gene_name })),
        ...(morphs.combos||[]).map(c => ({ ...c, type:'combo', name: c.combo_name, name_cn: c.combo_name_cn, formula: c.combo_formula }))
      ];
      
      // Score
      const answers = this.data.answers;
      const scores = [];
      
      for (const m of allMorphs) {
        let score = 0;
        let maxScore = 0;
        for (const ans of answers) {
          const matching = rules[ans] || [];
          maxScore++;
          // Check if this morph name or gene_symbol matches
          const mName = (m.gene_symbol || m.combo_name || m.name || '').toLowerCase();
          if (matching.some(r => mName.includes(r) || r === 'normal')) {
            score++;
          }
          // Also check formula for combos
          if (m.formula && matching.some(r => m.formula.toLowerCase().includes(r))) {
            score += 0.5;
          }
        }
        const pct = Math.round((score / Math.max(maxScore, 1)) * 100);
        if (pct > 10) scores.push({ ...m, score: pct });
      }
      
      scores.sort((a,b) => b.score - a.score);
      
      // Attach prices
      const priceRes = await app.request('/api/v2/prices/morphs', { data: { species_id: this.data.selSpecies } });
      const prices = priceRes.list || priceRes.data || [];
      const priceMap = {};
      for (const p of prices) {
        priceMap[p.symbol] = p;
      }
      
      const matches = scores.slice(0, 8).map(s => {
        const p = priceMap[s.gene_symbol || s.combo_name || s.name];
        return {
          name: s.gene_symbol || s.combo_name || s.name,
          name_cn: s.gene_name_cn || s.combo_name_cn || s.gene_name,
          type: s.type,
          formula: s.formula,
          desc: s.description,
          score: s.score,
          price_low: p ? p.price_range_low : null,
          price_high: p ? p.price_range_high : null,
        };
      });
      
      this.setData({ matches, loading: false, morphCount: allMorphs.length });
    } catch {
      this.setData({ loading: false });
    }
  },

  reset() { this.setData({ step: 1, selSpecies: null, matches: null, answers: [], selAnswers: {} }); }
});
