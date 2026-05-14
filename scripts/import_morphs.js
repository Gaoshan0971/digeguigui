#!/usr/bin/env node
// morph_import.js v2 — 品系种子数据入仓
const path = require('path');
const fs = require('fs');
const Database = require(require('path').join(__dirname, '..', 'server', 'node_modules', 'better-sqlite3'));

const DB = path.join(__dirname, '..', 'data', 'digeguigui.db');
const db = new Database(DB);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = OFF');

// Run migration
const sql = fs.readFileSync(path.join(__dirname, '..', 'data', 'morph_schema.sql'), 'utf-8');
db.exec(sql);
console.log('✅ Schema ready');

const sources = [
  ['morphs_cornsnake.json', 'Pantherophis guttatus'],
  ['morphs_ballpython.json', 'Python regius'],
  ['morphs_leopardgecko.json', 'Eublepharis macularius'],
];

const insGene = db.prepare("INSERT OR IGNORE INTO morph_genes (gene_symbol,gene_name,gene_name_cn,inheritance,category,description,is_proven) VALUES (?,?,?,?,?,?,1)");
const insMorph = db.prepare("INSERT OR IGNORE INTO species_morphs (species_id,gene_id,morph_name,morph_name_cn,is_base_morph) VALUES (?,?,?,?,1)");
const getGene = db.prepare("SELECT gene_id FROM morph_genes WHERE gene_symbol=?");
const getSpecies = db.prepare("SELECT species_id, name_cn FROM species WHERE name_latin LIKE ?");

let totalGenes = 0, totalMorphs = 0;

for (const [file, latinLike] of sources) {
  const fp = path.join(__dirname, '..', 'data', file);
  if (!fs.existsSync(fp)) { console.log(`⚠️  Missing ${file}`); continue; }

  const data = JSON.parse(fs.readFileSync(fp, 'utf-8'));
  const sp = getSpecies.get(latinLike + '%');
  if (!sp) { console.log(`⚠️  Species not in DB: ${latinLike}`); continue; }
  console.log(`\n🧬 [${sp.species_id}] ${sp.name_cn} — ${data.gene_count} genes...`);

  const tx = db.transaction(() => {
    let speciesAdded = 0;
    for (const g of data.genes) {
      insGene.run(g.gene_symbol, g.gene_name, g.gene_name_cn||'', g.inheritance||'recessive', g.category||'', g.description||'');
      const geneRow = getGene.get(g.gene_symbol);
      if (!geneRow) { console.log(`  ❌ Gene not inserted: ${g.gene_symbol}`); continue; }
      insMorph.run(sp.species_id, geneRow.gene_id, g.gene_name, g.gene_name_cn||'');
      totalGenes++;
      totalMorphs++;
      speciesAdded++;
    }
    return speciesAdded;
  });
  const added = tx();
  console.log(`  ✅ ${added} morphs linked`);
}

// Stats
const stats = db.prepare(`
  SELECT s.name_cn, COUNT(sm.morph_id) as cnt
  FROM species_morphs sm JOIN species s ON s.species_id=sm.species_id
  GROUP BY sm.species_id ORDER BY cnt DESC
`).all();

console.log('\n📊 品系入仓:');
for (const r of stats) console.log(`  ${r.name_cn}: ${r.cnt} 品系`);
console.log(`  总计: ${db.prepare('SELECT COUNT(*) as c FROM morph_genes').get().c} 基因定义 | ${totalMorphs} 物种关联`);

db.pragma('foreign_keys = ON');
db.close();
