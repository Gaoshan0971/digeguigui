#!/usr/bin/env node
/**
 * TTS品系变体 → morph_genes + morph_prices 入库
 * 用法: node scripts/import_turtle_morphs.js
 */

const path = require('path');
const fs = require('fs');
const Database = require(path.join(__dirname, '..', 'server', 'node_modules', 'better-sqlite3'));

const DB_PATH = path.join(__dirname, '..', 'data', 'digeguigui.db');
const TTS_FILE = path.join(__dirname, '..', 'data', 'tts_products.json');

// ── 学名映射 ──
const SPECIES_LATIN = {
    'red eared slider': 'Trachemys scripta elegans',
    'yellow bellied slider': 'Trachemys scripta scripta',
    'florida red belly': 'Pseudemys nelsoni',
    'common snapping turtle': 'Chelydra serpentina',
    'pink belly sideneck': 'Emydura subglobosa',
    'chinese box turtle': 'Cuora flavomarginata',
    'chinese golden box': 'Cuora flavomarginata',
    'red footed tortoise': 'Chelonoidis carbonarius',
    'red foot tortoise': 'Chelonoidis carbonarius',
};

// ── 品系表头映射 (TTS tag → morph_gene symbol) ──
const GENE_DEFS = {
    'albino': {
        gene_symbol: 'ALBINO',
        gene_name_cn: '白化',
        inheritance: 'recessive',
        category: '颜色',
        description: '缺乏黑色素，呈现白色/黄色/粉色体色，眼睛红色',
    },
    'charcoal': {
        gene_symbol: 'CHARCOAL',
        gene_name_cn: '炭黑',
        inheritance: 'recessive',
        category: '颜色',
        description: '深色变体，壳色呈炭黑色，纹路暗淡',
    },
    'hypo': {
        gene_symbol: 'HYPO',
        gene_name_cn: '减黑',
        inheritance: 'recessive',
        category: '颜色',
        description: 'Hypomelanistic — 黑色素减少，体色更亮',
    },
    'melanistic': {
        gene_symbol: 'MELANISTIC',
        gene_name_cn: '黑化',
        inheritance: 'recessive',
        category: '颜色',
        description: '黑色素过量，全身呈深黑色',
    },
    'leucistic': {
        gene_symbol: 'LEUCISTIC',
        gene_name_cn: '白变',
        inheritance: 'recessive',
        category: '颜色',
        description: '部分色素缺失，白色体色但眼睛正常色',
    },
    'paradox': {
        gene_symbol: 'PARADOX',
        gene_name_cn: '矛盾',
        inheritance: 'incomplete_dominant',
        category: '颜色',
        description: '体色呈现不规则色块分布，每只独一无二',
    },
    'translucent': {
        gene_symbol: 'TRANSLUCENT',
        gene_name_cn: '透明',
        inheritance: 'recessive',
        category: '颜色',
        description: '皮肤/甲壳透明度增加，可见内部结构',
    },
    'emerald': {
        gene_symbol: 'EMERALD',
        gene_name_cn: '翡翠',
        inheritance: 'incomplete_dominant',
        category: '颜色',
        description: '绿色调变体，壳色呈翡翠绿色',
    },
    'golden': {
        gene_symbol: 'GOLDEN',
        gene_name_cn: '金色',
        inheritance: 'recessive',
        category: '颜色',
        description: '黄色/金色体色变体',
    },
    'flame': {
        gene_symbol: 'FLAME',
        gene_name_cn: '火焰',
        inheritance: 'incomplete_dominant',
        category: '纹路',
        description: '红色/橙色斑纹加强，如火焰般鲜艳',
    },
    'platinum': {
        gene_symbol: 'PLATINUM',
        gene_name_cn: '铂金',
        inheritance: 'recessive',
        category: '颜色',
        description: '银白色高级变体',
    },
    't-positive': {
        gene_symbol: 'T_POS_ALBINO',
        gene_name_cn: 'T+白化',
        inheritance: 'recessive',
        category: '颜色',
        description: 'Tyrosinase-positive albino — 部分色素保留，非完全白化',
    },
    't-': {
        gene_symbol: 'T_NEG_ALBINO',
        gene_name_cn: 'T-白化',
        inheritance: 'recessive',
        category: '颜色',
        description: 'Tyrosinase-negative albino — 完全白化，无黑色素',
    },
    'heterozygous': {
        gene_symbol: 'HET',
        gene_name_cn: '隐带',
        inheritance: 'recessive',
        category: '其他',
        description: '携带隐性基因但不表现 — 育种价值',
    },
    'hybrid': {
        gene_symbol: 'HYBRID',
        gene_name_cn: '杂交',
        inheritance: 'polygenic',
        category: '其他',
        description: '跨亚种/种杂交后代',
    },
};

function main() {
    const db = new Database(DB_PATH);
    db.pragma('journal_mode = WAL');
    
    const products = JSON.parse(fs.readFileSync(TTS_FILE, 'utf8'));
    const morphProducts = products.filter(p => p.morph_tags && p.morph_tags.length > 0);
    
    console.log(`🧬 Processing ${morphProducts.length} morph products...\n`);
    
    let genesAdded = 0, morphsAdded = 0, pricesAdded = 0;
    
    // Prep statements
    const insertGene = db.prepare(`
        INSERT OR IGNORE INTO morph_genes (gene_symbol, gene_name, gene_name_cn, inheritance, category, description, source_url)
        VALUES (?, ?, ?, ?, ?, ?, 'https://theturtlesource.com')
    `);
    
    const getGeneId = db.prepare('SELECT gene_id FROM morph_genes WHERE gene_symbol = ?');
    
    const insertSpeciesMorph = db.prepare(`
        INSERT OR IGNORE INTO species_morphs (species_id, gene_id, morph_name, rarity)
        VALUES (?, ?, ?, 'rare')
    `);
    
    const insertMorphPrice = db.prepare(`
        INSERT OR IGNORE INTO morph_prices (species_id, gene_id, visual_price, currency, rarity)
        VALUES (?, ?, ?, 'USD', 'rare')
    `);
    
    // Also add species_prices for base species
    const insertSpeciesPrice = db.prepare(`
        INSERT OR IGNORE INTO species_prices (species_id, normal_low, currency)
        VALUES (?, ?, 'USD')
    `);
    
    for (const prod of morphProducts) {
        const name = (prod.name || '').toLowerCase();
        const tags = prod.morph_tags;
        const price = prod.price;
        
        // Find species
        let speciesName = null;
        for (const [key, latin] of Object.entries(SPECIES_LATIN)) {
            if (name.includes(key)) {
                speciesName = key;
                break;
            }
        }
        
        if (!speciesName) {
            console.log(`  ⚠️ Unknown species: ${prod.name}`);
            continue;
        }
        
        const latin = SPECIES_LATIN[speciesName];
        const species = db.prepare('SELECT species_id FROM species WHERE name_latin LIKE ? || \'%\' LIMIT 1').get(latin);
        
        if (!species) {
            console.log(`  ❌ Species not in DB: ${latin}`);
            continue;
        }
        
        console.log(`  🐢 ${prod.name}`);
        console.log(`     → ${latin} (species_id=${species.species_id})`);
        console.log(`     → 品系: ${tags.join(', ')}`);
        
        for (const tag of tags) {
            const def = GENE_DEFS[tag];
            if (!def) {
                console.log(`     ⚠️ Unknown tag: ${tag}`);
                continue;
            }
            
            // Insert gene definition
            insertGene.run(def.gene_symbol, def.gene_symbol, def.gene_name_cn || '', def.inheritance, def.category, def.description);
            const gene = getGeneId.get(def.gene_symbol);
            
            if (gene) {
                // Link to species
                const morphName = `${def.gene_name_cn || def.gene_symbol} ${prod.name.split(' ').slice(0, 3).join(' ')}`;
                const result = insertSpeciesMorph.run(species.species_id, gene.gene_id, morphName);
                if (result.changes > 0) morphsAdded++;
                
                // Add price
                if (price && price.min) {
                    insertMorphPrice.run(species.species_id, gene.gene_id, price.min);
                    pricesAdded++;
                }
                
                console.log(`       ✅ ${def.gene_symbol} (${def.name_cn}) → morph_genes + species_morphs`);
            }
        }
        
        // Add base species price
        if (price && price.min) {
            insertSpeciesPrice.run(species.species_id, price.min);
        }
    }
    
    console.log(`\n📊 Summary:`);
    console.log(`  Genes added: ${genesAdded}`);
    console.log(`  Species-morph links: ${morphsAdded}`);
    console.log(`  Prices added: ${pricesAdded}`);
    
    // Show current turtle morph stats
    const stats = db.prepare(`
        SELECT COUNT(DISTINCT mg.gene_id) as gene_count 
        FROM species s
        JOIN species_morphs sm ON s.species_id = sm.species_id
        JOIN morph_genes mg ON sm.gene_id = mg.gene_id
        WHERE s.category = '龟'
    `).get();
    
    console.log(`  龟类品系基因总数: ${stats.gene_count}`);
    
    db.close();
}

main();
