/**
 * 繁育计划 API — 龟类基因计算器 + 子代价值预估
 * 
 * GET /api/v2/breeding/calculate
 *   基因计算器
 *   参数: species_id, male=visual+albino, female=het+albino
 * 
 * GET /api/v2/breeding/estimate
 *   子代价值预估
 *   参数: species_id, male=visual+albino, female=het+albino, grade=B
 */

const db = require('../db');

// ── Punnett 计算 ──
function punnett(parent1Alleles, parent2Alleles, inheritance) {
  const results = {};
  for (const a1 of parent1Alleles) {
    for (const a2 of parent2Alleles) {
      const combo = [a1, a2].sort().join('');
      results[combo] = (results[combo] || 0) + 1;
    }
  }
  const total = parent1Alleles.length * parent2Alleles.length;
  
  // Map to phenotype
  const phenotypes = {};
  for (const [genotype, count] of Object.entries(results)) {
    let phenotype;
    if (inheritance === 'recessive') {
      // aa = visual, Aa/AA = normal or het
      phenotype = genotype === 'aa' ? 'visual' : (genotype.includes('A') && genotype.includes('a') ? 'het' : 'normal');
    } else if (inheritance === 'dominant') {
      phenotype = genotype.includes('A') ? 'visual' : 'normal';
    } else if (inheritance === 'codominant' || inheritance === 'incomplete_dominant') {
      if (genotype === 'AA') phenotype = 'super';
      else if (genotype === 'Aa' || genotype === 'aA') phenotype = 'visual';
      else phenotype = 'normal';
    } else {
      phenotype = 'unknown';
    }
    phenotypes[phenotype] = (phenotypes[phenotype] || 0) + count;
  }
  
  return {
    genotypes: results,
    phenotypes,
    total,
    probabilities: Object.fromEntries(
      Object.entries(phenotypes).map(([k, v]) => [k, Math.round(v / total * 10000) / 100])
    ),
  };
}

// 解析亲本基因型
function parseGenotype(input) {
  // Format: "visual albino" or "het albino" or just "albino" (default het)
  if (!input || input === 'normal') return { type: 'normal', gene: null, alleles: ['A', 'A'] };
  
  const parts = input.toLowerCase().trim().split(/\s+/);
  let type = 'het';
  let gene = null;
  
  for (const part of parts) {
    if (['visual', 'super', 'het', 'heterozygous'].includes(part)) {
      type = part === 'heterozygous' ? 'het' : part;
    } else {
      gene = part.toUpperCase();
    }
  }
  
  // Map to alleles
  const alleles = type === 'visual' ? ['a', 'a'] :
                  type === 'super' ? ['A', 'A'] :
                  type === 'het' ? ['A', 'a'] :
                  ['A', 'A'];
  
  return { type, gene, alleles };
}

const GRADE_COEFF = { 'S': 3.5, 'A+': 2.5, 'A': 1.8, 'A-': 1.3, 'B+': 1.1, 'B': 1.0, 'C': 0.6 };

function register(app) {
  // ==================== 基因计算器 ====================
  app.get('/api/v2/breeding/calculate', (req, res) => {
    const { species_id, male, female } = req.query;
    
    if (!species_id || !male || !female) {
      return res.status(400).json({ ok: false, error: '需要 species_id, male, female 参数' });
    }
    
    const species = db.prepare('SELECT name_cn, name_latin FROM species WHERE species_id = ?').get(species_id);
    if (!species) return res.status(404).json({ ok: false, error: '品种不存在' });
    
    // 获取该品种的所有品系基因
    const morphGenes = db.prepare(`
      SELECT mg.gene_symbol, mg.gene_name_cn, mg.inheritance, mg.description,
             MIN(COALESCE(mp.visual_price, 0)) as visual_price,
             MIN(COALESCE(mp.het_price, 0)) as het_price
      FROM species_morphs sm
      JOIN morph_genes mg ON sm.gene_id = mg.gene_id
      LEFT JOIN morph_prices mp ON mp.gene_id = mg.gene_id AND mp.species_id = sm.species_id
      WHERE sm.species_id = ?
      GROUP BY mg.gene_symbol
    `).all(species_id);
    
    if (morphGenes.length === 0) {
      return res.json({
        ok: true,
        data: {
          species,
          message: '该品种暂无品系基因数据，无法计算',
          results: [],
        },
      });
    }
    
    // 解析亲本
    const parent1 = parseGenotype(male);
    const parent2 = parseGenotype(female);
    
    // 对每个基因分别计算
    const results = [];
    
    for (const mg of morphGenes) {
      // 如果亲本指定了具体基因，只计算匹配的
      if (parent1.gene && parent1.gene !== mg.gene_symbol) continue;
      if (parent2.gene && parent2.gene !== mg.gene_symbol) continue;
      
      const p1Alleles = parent1.gene === mg.gene_symbol ? parent1.alleles : ['A', 'A'];
      const p2Alleles = parent2.gene === mg.gene_symbol ? parent2.alleles : ['A', 'A'];
      
      const calc = punnett(p1Alleles, p2Alleles, mg.inheritance);
      
      results.push({
        gene_symbol: mg.gene_symbol,
        gene_name: mg.gene_name_cn || mg.gene_symbol,
        inheritance: mg.inheritance,
        parent1: parent1.type,
        parent2: parent2.type,
        offspring: calc.probabilities,
        // 子代可能品系及价格
        offspring_values: Object.entries(calc.probabilities).map(([phenotype, prob]) => {
          let price = 0;
          if (phenotype === 'visual') price = mg.visual_price || 0;
          else if (phenotype === 'het') price = mg.het_price || 0;
          else if (phenotype === 'super') price = mg.super_price || (mg.visual_price || 0) * 2;
          
          return {
            phenotype,
            probability: prob,
            price,
            label: phenotype === 'visual' ? '表现型' :
                   phenotype === 'super' ? '超级型' :
                   phenotype === 'het' ? '隐带' : '普通',
          };
        }),
      });
    }
    
    res.json({
      ok: true,
      data: {
        species,
        parents: {
          male: parent1.type,
          female: parent2.type,
        },
        total_genes: morphGenes.length,
        results,
      },
    });
  });
  
  // ==================== 子代价值预估 ====================
  app.get('/api/v2/breeding/estimate', (req, res) => {
    const { species_id, male, female, grade = 'B' } = req.query;
    
    if (!species_id) {
      return res.status(400).json({ ok: false, error: '需要 species_id' });
    }
    
    const gradeCoeff = GRADE_COEFF[grade.toUpperCase()] || 1.0;
    
    // 先跑基因计算
    // 简化：从基因计算器获取结果
    const species = db.prepare('SELECT name_cn, name_latin FROM species WHERE species_id = ?').get(species_id);
    if (!species) return res.status(404).json({ ok: false, error: '品种不存在' });
    
    // 基础价
    const speciesPrice = db.prepare('SELECT normal_low, normal_high FROM species_prices WHERE species_id = ?').get(species_id);
    let baseLow = speciesPrice?.normal_low || 0;
    
    if (!baseLow) {
      const sp = db.prepare('SELECT market_data FROM species WHERE species_id = ?').get(species_id);
      if (sp?.market_data) {
        try {
          const md = JSON.parse(sp.market_data);
          if (md.tts_price) {
            const tts = typeof md.tts_price === 'string' ? JSON.parse(md.tts_price) : md.tts_price;
            baseLow = tts.min || 0;
          }
          if (!baseLow && md.bw_price) baseLow = md.bw_price || 0;
        } catch(e) {}
      }
    }
    
    // 如果指定了亲本基因型，计算子代价值和概率分布
    const offspringEstimates = [];
    let totalWeightedValue = 0;
    let totalProb = 0;
    
    if (male && female) {
      // 重新调基因计算
      const morphGenes = db.prepare(`
        SELECT mg.gene_symbol, mg.gene_name_cn, mg.inheritance,
               COALESCE(mp.visual_price, 0) as visual_price,
               COALESCE(mp.het_price, 0) as het_price
        FROM species_morphs sm
        JOIN morph_genes mg ON sm.gene_id = mg.gene_id
        LEFT JOIN morph_prices mp ON mp.gene_id = mg.gene_id AND mp.species_id = sm.species_id
        WHERE sm.species_id = ?
      `).all(species_id);
      
      const p1 = parseGenotype(male);
      const p2 = parseGenotype(female);
      
      for (const mg of morphGenes) {
        if (p1.gene && p1.gene !== mg.gene_symbol) continue;
        if (p2.gene && p2.gene !== mg.gene_symbol) continue;
        
        const p1A = p1.gene === mg.gene_symbol ? p1.alleles : ['A', 'A'];
        const p2A = p2.gene === mg.gene_symbol ? p2.alleles : ['A', 'A'];
        const calc = punnett(p1A, p2A, mg.inheritance);
        
        for (const [phenotype, prob] of Object.entries(calc.probabilities)) {
          let price = 0;
          if (phenotype === 'visual') price = mg.visual_price;
          else if (phenotype === 'het') price = mg.het_price;
          
          const value = Math.round((baseLow + price) * gradeCoeff);
          offspringEstimates.push({
            gene: mg.gene_symbol,
            gene_name: mg.gene_name_cn || mg.gene_symbol,
            phenotype,
            probability: prob,
            estimated_value: value,
          });
          
          totalWeightedValue += value * prob;
          totalProb += prob;
        }
      }
    }
    
    const avgOffspringValue = totalProb > 0 ? Math.round(totalWeightedValue / totalProb) : baseLow;
    
    res.json({
      ok: true,
      data: {
        species,
        base_price: baseLow,
        grade: { level: grade.toUpperCase(), coefficient: gradeCoeff },
        clutch_estimate: {
          avg_per_offspring: avgOffspringValue,
          formula: 'Σ(基因型概率 × (基础价 + 品系溢价)) × 品级系数',
        },
        offspring_distribution: offspringEstimates,
        tip: '龟类每窝产卵量因品种而异（2-30枚），以上为单只子代估值。',
      },
    });
  });
  
  // ==================== 品系参考 ====================
  app.get('/api/v2/breeding/genes', (req, res) => {
    const { species_id } = req.query;
    
    let genes;
    if (species_id) {
      genes = db.prepare(`
        SELECT mg.gene_symbol, mg.gene_name_cn, mg.inheritance, mg.category, mg.description,
               mp.visual_price, mp.het_price
        FROM species_morphs sm
        JOIN morph_genes mg ON sm.gene_id = mg.gene_id
        LEFT JOIN morph_prices mp ON mp.gene_id = mg.gene_id AND mp.species_id = sm.species_id
        WHERE sm.species_id = ?
        ORDER BY mg.inheritance, mg.gene_symbol
      `).all(species_id);
    } else {
      // All turtle genes
      genes = db.prepare(`
        SELECT DISTINCT mg.gene_symbol, mg.gene_name_cn, mg.inheritance, mg.category, mg.description,
               s.name_cn as species_name
        FROM morph_genes mg
        JOIN species_morphs sm ON mg.gene_id = sm.gene_id
        JOIN species s ON sm.species_id = s.species_id
        WHERE s.category = '龟'
        ORDER BY s.name_cn, mg.gene_symbol
      `).all();
    }
    
    // 遗传模式说明
    const inheritanceGuide = {
      recessive: '隐性遗传 — 需双亲各提供一个隐性等位基因才表现。het×het=25% visual',
      dominant: '显性遗传 — 只要一个等位基因即表现。visual×normal=50% visual',
      codominant: '共显性 — 杂合=中间型，纯合=超级型。visual×visual=25% super',
      incomplete_dominant: '不完全显性 — 同共显性。visual×visual=25% super, 50% visual',
      polygenic: '多基因 — 多个基因共同作用，子代表现连续分布',
    };
    
    res.json({
      ok: true,
      data: {
        genes,
        inheritance_guide: inheritanceGuide,
        usage: {
          calculator: 'GET /api/v2/breeding/calculate?species_id=X&male=visual+albino&female=het+albino',
          estimate: 'GET /api/v2/breeding/estimate?species_id=X&male=visual+albino&female=het+albino&grade=A',
          syntax: '亲本格式: normal | het GENE | visual GENE | super GENE (如: "visual albino", "het charcoal")',
        },
      },
    });
  });
}

module.exports = { register };
