#!/usr/bin/env node
// 异宠数据入仓
const Database = require(require('path').join(__dirname, '..', 'server', 'node_modules', 'better-sqlite3'));
const path = require('path');
const fs = require('fs');

const DB_PATH = path.join(__dirname, '..', 'data', 'digeguigui.db');
const JSON_PATH = path.join(__dirname, '..', 'data', 'species_exotics.json');

const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

require('../server/db'); // 确保 schema + migration

// 加 category 列
try { db.exec("ALTER TABLE species ADD COLUMN category TEXT DEFAULT ''"); } catch(e) {}
try { db.exec("ALTER TABLE species ADD COLUMN class_name TEXT DEFAULT ''"); } catch(e) {}

// Create unique index
try { db.exec('CREATE UNIQUE INDEX IF NOT EXISTS idx_species_latin ON species(name_latin)'); } catch(e) {}

const data = JSON.parse(fs.readFileSync(JSON_PATH, 'utf-8'));

const upsert = db.prepare(`
  INSERT INTO species (
    name_cn, name_latin, common_name_en, family, genus,
    distribution, habitat, conservation, reproduction, etymology,
    image_url, image_attribution, image_license,
    wikipedia_url, observations_count,
    overview, traits, care_params, category, class_name
  ) VALUES (
    @name_cn, @name_latin, @common_name_en, @family, @genus,
    @distribution, @habitat, @conservation, @reproduction, @etymology,
    @image_url, @image_attribution, @image_license,
    @wikipedia_url, @observations_count,
    @overview, @traits, @care_params, @category, @class_name
  )
  ON CONFLICT(name_latin) DO UPDATE SET
    name_cn = excluded.name_cn,
    common_name_en = COALESCE(excluded.common_name_en, species.common_name_en),
    family = COALESCE(excluded.family, species.family),
    genus = COALESCE(excluded.genus, species.genus),
    distribution = COALESCE(excluded.distribution, species.distribution),
    habitat = COALESCE(excluded.habitat, species.habitat),
    conservation = COALESCE(excluded.conservation, species.conservation),
    reproduction = COALESCE(excluded.reproduction, species.reproduction),
    etymology = COALESCE(excluded.etymology, species.etymology),
    image_url = COALESCE(excluded.image_url, species.image_url),
    image_attribution = COALESCE(excluded.image_attribution, species.image_attribution),
    image_license = COALESCE(excluded.image_license, species.image_license),
    wikipedia_url = COALESCE(excluded.wikipedia_url, species.wikipedia_url),
    observations_count = COALESCE(excluded.observations_count, species.observations_count),
    category = COALESCE(excluded.category, species.category),
    class_name = COALESCE(excluded.class_name, species.class_name)
`);

// Class mapping: 龟类=Testudines, 蛇=Serpentes, 蜥蜴=Lacertilia, 蛙=Anura
const classCN = {
  'Reptilia': '爬行纲',
  'Amphibia': '两栖纲',
  'Testudines': '龟鳖目',
  'Squamata': '有鳞目',
  'Anura': '无尾目',
};

function classify(s) {
  const cls = (s.class || '').toLowerCase();
  const fam = (s.family || '').toLowerCase();
  if (cls.includes('amphibia') || fam.includes('dae') && ['ceratophryidae','pelodryadidae','microhylidae','pyxicephalidae','phyllomedusidae','hylidae','rhacophoridae'].includes(fam)) return '蛙';
  if (fam === 'colubridae' || fam === 'pythonidae' || fam === 'boidae' || fam === 'viperidae' || fam === 'elapidae') return '蛇';
  if (fam === 'eublepharidae' || fam === 'diplodactylidae' || fam === 'gekkonidae' || fam === 'pygopodidae' || fam === 'sphaerodactylidae' || fam === 'phyllodactylidae') return '守宫';
  if (fam === 'agamidae' || fam === 'iguanidae' || fam === 'chamaeleonidae' || fam === 'varanidae' || fam === 'teiidae' || fam === 'scincidae' || fam === 'crotaphytidae' || fam === 'gerrhosauridae' || fam === 'dactyloidae' || fam === 'helodermatidae' || fam === 'lacertidae' || fam === 'cordylidae') return '蜥蜴';
  return '其他';
}

let inserted = 0, updated = 0;
const insertAll = db.transaction(() => {
  for (const s of data) {
    if (s.error) continue;
    const existing = db.prepare('SELECT species_id FROM species WHERE name_latin = ?').get(s.name_latin);
    upsert.run({
      name_cn: s.name_cn,
      name_latin: s.name_latin,
      common_name_en: s.common_name_en || '',
      family: s.family || '',
      genus: s.genus || '',
      distribution: s.distribution || '',
      habitat: s.habitat || '',
      conservation: s.conservation || '',
      reproduction: s.reproduction || '',
      etymology: s.etymology || '',
      image_url: s.image_url || '',
      image_attribution: s.image_attribution || '',
      image_license: s.image_license || '',
      wikipedia_url: s.wikipedia_url || '',
      observations_count: s.observations_count || 0,
      overview: s.overview || '',
      traits: JSON.stringify(s.traits || {}),
      care_params: JSON.stringify(s.care_params || {}),
      category: classify(s),
      class_name: s.class || '',
    });
    if (existing) updated++; else inserted++;
  }
});
insertAll();

// Summary
const stats = db.prepare("SELECT category, COUNT(*) as cnt FROM species GROUP BY category ORDER BY cnt DESC").all();
console.log(`\n📥 异宠入库: 新增 ${inserted} / 更新 ${updated}`);
console.log('📊 基因库品类:');
for (const r of stats) {
  console.log(`  ${r.category || '未分类'}: ${r.cnt} 种`);
}

const total = db.prepare("SELECT COUNT(*) as cnt FROM species").get();
console.log(`\n🐾 基因库总计: ${total.cnt} 种`);
db.close();
