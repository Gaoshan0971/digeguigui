/**
 * 品种详情聚合 + 价值预估 API
 * 
 * GET /api/v2/species/:id/profile
 *   一站式品种档案：分类+饲养+市场+品系+品鉴标准
 *   参数: ?user_token=xxx  (获取用户品鉴记录)
 * 
 * GET /api/v2/species/:id/value
 *   价值预估：基础价 + 品系溢价 × 品级系数
 *   参数: ?genes=albino,hypo&grade=A+
 * 
 * GET /api/v2/species/value/calculate
 *   定价公式参考说明
 */

const db = require('../db');
const fs = require('fs');
const path = require('path');

// ── 品级系数 ──
const GRADE_COEFFICIENTS = {
  'S':  3.5,
  'A+': 2.5,
  'A':  1.8,
  'A-': 1.3,
  'B+': 1.1,
  'B':  1.0,
  'C':  0.6,
};

// ── 品鉴维度说明 ──
const APPRAISAL_DIMENSIONS = {
  shell: {
    name: '壳形',
    description: '甲壳完整度、对称性、隆起弧度、缘盾整齐度',
    weight: 0.30,
    rubric: {
      '9-10': '完美对称，高拱饱满，缘盾整齐无缺刻，生长纹均匀',
      '7-8': '基本对称，轻微不平整，缘盾有1-2处小缺刻',
      '5-6': '可见不对称，轻微隆背，缘盾缺刻明显',
      '3-4': '明显畸形，隆背严重，缘盾缺损',
      '1-2': '严重畸形，甲壳塌陷或过度隆起',
    },
  },
  head: {
    name: '头部',
    description: '头型比例、眼睛明亮度、喙部完整、头部花纹',
    weight: 0.20,
    rubric: {
      '9-10': '头型饱满标准，眼睛明亮有神，喙部完整无磨损，花纹清晰',
      '7-8': '头型基本标准，眼睛清澈，喙部轻微磨损',
      '5-6': '头部偏小或偏大，眼睛略浑浊，喙部磨损可见',
      '3-4': '头部明显不标准，眼睛浑浊或凹陷，喙部严重磨损',
      '1-2': '头部畸形，眼睛病变，喙部缺损',
    },
  },
  color: {
    name: '色泽',
    description: '体色鲜艳度、花纹对比度、色素分布均匀度',
    weight: 0.25,
    rubric: {
      '9-10': '色泽极其鲜艳，花纹对比强烈，色素分布极为均匀，发色完美',
      '7-8': '色泽鲜明，花纹清晰可辨，色素分布较均匀',
      '5-6': '色泽一般，花纹模糊，色素分布有斑驳',
      '3-4': '色泽暗淡，花纹几乎不可见',
      '1-2': '色泽灰暗，无花纹，色素异常',
    },
  },
  body: {
    name: '体型',
    description: '体型比例、肥满度、四肢完整、尾部形态',
    weight: 0.15,
    rubric: {
      '9-10': '体型标准匀称，肥满度适中，四肢完整无伤，尾部形态完美',
      '7-8': '体型基本标准，轻微偏瘦或偏胖，四肢有轻微旧伤',
      '5-6': '体型偏瘦或偏胖，四肢有可见伤痕',
      '3-4': '体型明显不标准，过瘦或肥胖，四肢有残缺',
      '1-2': '极度消瘦或肥胖，四肢严重残缺',
    },
  },
  health: {
    name: '健康',
    description: '活跃度、呼吸状态、眼鼻分泌物、甲壳健康状况',
    weight: 0.10,
    rubric: {
      '9-10': '极为活跃，呼吸正常，眼鼻干净，甲壳无腐甲/烂甲，食欲旺盛',
      '7-8': '活跃度正常，呼吸正常，无分泌物，甲壳有小面积旧伤',
      '5-6': '活跃度一般，偶有张口呼吸，轻微眼鼻分泌物',
      '3-4': '明显嗜睡，呼吸急促或有声，眼鼻分泌物明显，甲壳有腐甲',
      '1-2': '极度萎靡，呼吸困难，严重腐甲/烂甲，拒食',
    },
  },
};

// ── 饲养决策字段 ──
const CARE_DECISION_FIELDS = [
  { key: 'temp_min', label: '最低温度(℃)', icon: '🌡️', suffix: '°C', tip: '低于此温度需加温' },
  { key: 'temp_max', label: '最高温度(℃)', icon: '🌡️', suffix: '°C', tip: '晒点温度/热区温度' },
  { key: 'humidity', label: '湿度', icon: '💧', suffix: '%', tip: '环境适宜湿度范围' },
  { key: 'uvb', label: 'UVB需求', icon: '☀️', tip: '紫外线灯需求等级' },
  { key: 'enclosure', label: '饲养容器', icon: '🏠', tip: '推荐饲养容器类型和大小' },
  { key: 'substrate', label: '垫材', icon: '🪨', tip: '推荐底材类型' },
  { key: 'diet', label: '食谱', icon: '🍽️', tip: '主要食物类型' },
  { key: 'lifespan', label: '寿命', icon: '⏳', suffix: '年', tip: '人工饲养预期寿命' },
  { key: 'difficulty', label: '饲养难度', icon: '📊', tip: '1-5星，1最简单' },
  { key: 'adult_size', label: '成体尺寸', icon: '📏', suffix: 'cm', tip: '成年后体型大小' },
  { key: 'activity', label: '活动习性', icon: '🏃', tip: '日行/夜行/晨昏活动' },
  { key: 'social', label: '群居性', icon: '👥', tip: '能否混养' },
];

function register(app) {
  const { getUser } = require('../middleware/auth');

  // ==================== 品种完整档案 ====================
  app.get('/api/v2/species/:id/profile', (req, res) => {
    const speciesId = req.params.id;
    const lang = (req.query.lang || 'zh').toLowerCase();

    // ── 1. 基础信息 ──
    const species = db.prepare(`
      SELECT species_id, name_cn, name_latin, common_name_en, family,
             genus, category, class_name, difficulty,
             overview, overview_en, distribution, habitat,
             conservation, reproduction, etymology,
             image_url, image_attribution, image_license,
             care_params, market_data, traits
      FROM species WHERE species_id = ?
    `).get(speciesId);

    if (!species) {
      return res.status(404).json({ ok: false, error: '品种不存在' });
    }

    // 解析 JSON 字段
    let careParams = {};
    try { careParams = JSON.parse(species.care_params || '{}'); } catch (e) { }
    let marketData = {};
    try { marketData = JSON.parse(species.market_data || '{}'); } catch (e) { }
    let traits = {};
    try { traits = JSON.parse(species.traits || '{}'); } catch (e) { }

    // ── 2. 饲养决策 ──
    const careSummary = CARE_DECISION_FIELDS.map(f => ({
      key: f.key,
      label: f.label,
      icon: f.icon,
      value: careParams[f.key] || null,
      suffix: f.suffix || '',
      tip: f.tip,
    }));

    // 难度星级
    const difficulty = species.difficulty || parseInt(careParams.difficulty) || 3;
    const difficultyLabel = ['', '⭐ 入门', '⭐⭐ 简单', '⭐⭐⭐ 中等', '⭐⭐⭐⭐ 较难', '⭐⭐⭐⭐⭐ 专家'][difficulty] || '⭐⭐⭐ 中等';

    // ── 3. 市场行情 ──
    // 国外参考价（三家美国站）
    const foreignPrices = [];
    if (marketData.sas_price) foreignPrices.push({ source: 'SnakesAtSunset', price: marketData.sas_price, url: marketData.sas_url });
    if (marketData.tts_price) {
      try {
        const ttsParsed = JSON.parse(marketData.tts_price);
        const ttsPrice = ttsParsed?.min || ttsParsed;
        foreignPrices.push({ source: 'TheTurtleSource', price: ttsPrice, url: marketData.tts_url });
      } catch (e) {
        foreignPrices.push({ source: 'TheTurtleSource', price: marketData.tts_price, url: marketData.tts_url });
      }
    }
    if (marketData.bw_price) foreignPrices.push({ source: 'BackwaterReptiles', price: marketData.bw_price, url: marketData.bw_url });
    
    const foreignMin = foreignPrices.length ? Math.min(...foreignPrices.map(p => parseFloat(p.price) || 0)) : null;
    const foreignMax = foreignPrices.length ? Math.max(...foreignPrices.map(p => parseFloat(p.price) || 0)) : null;
    
    const marketSection = {
      domestic: {
        sources: [],
        price_min: null,
        price_max: null,
        currency: 'CNY',
        has_data: false,
      },
      international: {
        price_min: foreignMin,
        price_max: foreignMax,
        currency: 'USD',
        has_data: foreignPrices.length > 0,
        source_count: foreignPrices.length,
        disclaimer: '国际行情参考价',
      },
      // 向后兼容
      tts: marketData.tts_price ? (() => {
        try { return JSON.parse(marketData.tts_price); } catch (e) { return null; }
      })() : null,
      bw: marketData.bw_price || null,
      tts_url: marketData.tts_url || null,
      bw_url: marketData.bw_url || null,
    };

    // ── 4. 品系基因 ──
    const morphGenes = db.prepare(`
      SELECT mg.gene_id, mg.gene_symbol, mg.gene_name_cn, mg.inheritance,
             mg.category as gene_category, mg.description,
             mp.visual_price, mp.het_price, mp.rarity
      FROM species_morphs sm
      JOIN morph_genes mg ON sm.gene_id = mg.gene_id
      LEFT JOIN morph_prices mp ON mp.gene_id = mg.gene_id AND mp.species_id = sm.species_id
      WHERE sm.species_id = ?
      ORDER BY mg.inheritance, mg.gene_symbol
    `).all(speciesId);

    const hasMorphs = morphGenes.length > 0;
    const morphCount = morphGenes.length;

    // ── 5. 品鉴标准 ──
    const appraisalRubric = {
      dimensions: APPRAISAL_DIMENSIONS,
      grade_labels: {
        'S':  { label: '典藏级', priceMultiplier: 3.5, description: '万里挑一，展览级品相' },
        'A+': { label: '极品', priceMultiplier: 2.5, description: '品相出众，远超同类' },
        'A':  { label: '优选', priceMultiplier: 1.8, description: '品相优良，值得收藏' },
        'A-': { label: '精品', priceMultiplier: 1.3, description: '品相不错，超过普货' },
        'B+': { label: '尚可', priceMultiplier: 1.1, description: '品相正常，无明显缺陷' },
        'B':  { label: '普货', priceMultiplier: 1.0, description: '正常个体，有轻微瑕疵' },
        'C':  { label: '练手', priceMultiplier: 0.6, description: '有缺陷，适合新手练手' },
      },
    };

    // ── 6. 训练数据 ──
    const speciesDir = `/tmp/turtle_dataset/${species.name_cn}`;
    let trainingCount = 0;
    try {
      if (fs.existsSync(speciesDir)) {
        trainingCount = fs.readdirSync(speciesDir).filter(f => f.endsWith('.jpg')).length;
      }
    } catch (e) { }

    // ── 7. 用户品鉴记录(如果登录) ──
    let userAppraisals = [];
    const token = req.query.user_token;
    if (token) {
      const user = getUser(req, res);
      if (!user) return;
      userAppraisals = db.prepare(`
        SELECT c.title, a.score_shell, a.score_head, a.score_color, a.score_body, a.score_health,
               a.grade, a.comment, a.created_at
        FROM appraisals a
        JOIN collections c ON a.collection_id = c.collection_id
        WHERE c.species_id = ? AND a.user_id = ?
        ORDER BY a.created_at DESC LIMIT 10
      `).all(speciesId, user.user_id);
    }

    res.json({
      ok: true,
      data: {
        // 基础
        species: {
          id: species.species_id,
          name_cn: species.name_cn,
          name_latin: species.name_latin,
          common_name_en: species.common_name_en || '',
          family: species.family,
          genus: species.genus || '',
          category: species.category,
          difficulty,
          difficulty_label: difficultyLabel,
          image: species.image_url || '',
          image_attr: species.image_attribution || '',
          image_license: species.image_license || '',
        },
        // 简介
        overview: lang === 'en' ? (species.overview_en || species.overview || '') : (species.overview || ''),
        distribution: species.distribution || '',
        habitat: species.habitat || '',
        conservation: species.conservation || '',
        reproduction: species.reproduction || '',
        etymology: species.etymology || '',
        // 饲养决策
        care: {
          summary: `${difficultyLabel} · ${careParams.lifespan || '?'} 年寿命 · 成体 ${careParams.adult_size || '?'}cm`,
          params: careSummary,
        },
        // 市场
        market: marketSection,
        // 品系
        morph: {
          has_morphs: hasMorphs,
          count: morphCount,
          genes: morphGenes,
        },
        // 品鉴标准
        appraisal: appraisalRubric,
        // 训练数据
        training: { image_count: trainingCount },
        // 用户品鉴
        user_appraisals: userAppraisals,
        // 可用服务（哪些有数据支撑，前端据此亮灯/置灰）
        available_services: {
          identify: !!(species.image_url || trainingCount > 0),
          care: Object.values(careParams).filter(v => v !== null && v !== undefined).length >= 3,
          appraisal: species.category === '龟' || species.category === '龟类',
          value: !!(marketData.sas_price || marketData.tts_price || marketData.bw_price),
          provenance: true,  // 始终可用，用户自主锚定
        },
      },
    });
  });

  // ==================== 价值预估 ====================
  app.get('/api/v2/species/:id/value', (req, res) => {
    const speciesId = req.params.id;
    const genesParam = (req.query.genes || '').toLowerCase();
    const grade = (req.query.grade || 'B').toUpperCase();

    const requestedGenes = genesParam ? genesParam.split(',').map(g => g.trim()).filter(Boolean) : [];

    // ── 基础价 ──
    const speciesPrice = db.prepare(`
      SELECT normal_low, normal_high, select_low, select_high, premium_low, premium_high, currency
      FROM species_prices WHERE species_id = ?
    `).get(speciesId);

    let baseLow = 0, baseHigh = 0, currency = 'CNY';

    if (speciesPrice) {
      baseLow = speciesPrice.normal_low;
      baseHigh = speciesPrice.normal_high;
      currency = speciesPrice.currency;
    }

    // ── TTS/BW 市场价格兜底 ──
    if (!baseLow) {
      const species = db.prepare('SELECT market_data FROM species WHERE species_id = ?').get(speciesId);
      if (species && species.market_data) {
        try {
          const md = JSON.parse(species.market_data);
          if (md.tts_price) {
            const tts = typeof md.tts_price === 'string' ? JSON.parse(md.tts_price) : md.tts_price;
            baseLow = tts.min || 0;
            baseHigh = tts.max || baseLow;
            currency = 'USD';
          }
          if (!baseLow && md.bw_price) {
            baseLow = md.bw_price;
            baseHigh = md.bw_price;
            currency = 'USD';
          }
        } catch (e) { }
      }
    }

    // ── 品系溢价 ──
    let morphPremium = 0;
    const morphDetails = [];

    if (requestedGenes.length > 0) {
      const placeholders = requestedGenes.map(() => '?').join(',');
      const genePrices = db.prepare(`
        SELECT mg.gene_symbol, mg.gene_name_cn, mp.visual_price, mp.het_price
        FROM morph_genes mg
        JOIN species_morphs sm ON mg.gene_id = sm.gene_id
        LEFT JOIN morph_prices mp ON mp.gene_id = mg.gene_id AND mp.species_id = sm.species_id
        WHERE sm.species_id = ? AND LOWER(mg.gene_symbol) IN (${placeholders})
      `).all(speciesId, ...requestedGenes);

      // 去重：同一基因取最低 visual_price
      const geneMap = {};
      for (const gp of genePrices) {
        const price = gp.visual_price || gp.het_price || 0;
        const key = gp.gene_symbol;
        if (!geneMap[key] || (price > 0 && price < geneMap[key].premium)) {
          geneMap[key] = {
            gene: gp.gene_symbol,
            name: gp.gene_name_cn || gp.gene_symbol,
            premium: price,
            price_type: gp.visual_price ? 'visual' : 'het',
            all_prices: [],
          };
        }
        if (geneMap[key]) {
          geneMap[key].all_prices.push(price);
        }
      }

      for (const entry of Object.values(geneMap)) {
        morphPremium += entry.premium;
        morphDetails.push(entry);
      }
    }

    // ── 品级系数 ──
    const gradeCoeff = GRADE_COEFFICIENTS[grade] || 1.0;

    // ── 计算 ──
    const estLow = Math.round((baseLow + morphPremium) * gradeCoeff);
    const estHigh = Math.round((baseHigh + morphPremium) * gradeCoeff);
    const estMid = Math.round((estLow + estHigh) / 2);

    const gradeLabel = {
      'S': '典藏级', 'A+': '极品', 'A': '优选', 'A-': '精品',
      'B+': '尚可', 'B': '普货', 'C': '练手',
    }[grade] || grade;

    res.json({
      ok: true,
      data: {
        formula: `估值 = (基础价 + 品系溢价) × 品级系数`,
        base_price: { low: baseLow, high: baseHigh, currency },
        morph_premium: {
          total: morphPremium,
          details: morphDetails,
        },
        grade: {
          level: grade,
          label: gradeLabel,
          coefficient: gradeCoeff,
        },
        estimate: {
          low: estLow,
          mid: estMid,
          high: estHigh,
          currency,
          display: `${currency} ${estLow} ~ ${estHigh}`,
        },
      },
    });
  });

  // ==================== 定价参考 ── ====================
  app.get('/api/v2/species/value/calculate', (req, res) => {
    res.json({
      ok: true,
      data: {
        formula: ['估值 = (基础价 + Σ品系溢价) × 品级系数'],
        grade_coefficients: GRADE_COEFFICIENTS,
        grade_labels: {
          S: '典藏级 ×3.5 — 赛级/展览级品相',
          'A+': '极品 ×2.5 — 远超同类标准',
          A: '优选 ×1.8 — 品相优良',
          'A-': '精品 ×1.3 — 超过普货',
          'B+': '尚可 ×1.1 — 无明显缺陷',
          B: '普货 ×1.0 — 正常个体基准价',
          C: '练手 ×0.6 — 有缺陷/瑕疵',
        },
        note: '价格仅供参考，实际成交价以买卖双方协商为准。品系溢价来自国际市场(TTS)公开售价。',
      },
    });
  });
}

module.exports = { register };
