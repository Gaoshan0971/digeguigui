#!/usr/bin/env node
/**
 * import_species.js — 权威数据入库（upsert 模式）
 * 用法: node scripts/import_species.js
 */
const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

const DB_PATH = path.join(__dirname, '..', 'data', 'digeguigui.db');
const JSON_PATH = path.join(__dirname, '..', 'data', 'species_authoritative.json');

const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

// 触发 migration（ALTER TABLE 补列）
require('../server/db');

const data = JSON.parse(fs.readFileSync(JSON_PATH, 'utf-8'));

// 先创建 UNIQUE 索引（如果还没）
try {
  db.exec('CREATE UNIQUE INDEX IF NOT EXISTS idx_species_latin ON species(name_latin)');
} catch (e) {}

const upsert = db.prepare(`
  INSERT INTO species (
    name_cn, name_latin, common_name_en, family, genus,
    distribution, habitat, conservation, reproduction, etymology,
    image_url, image_attribution, image_license,
    wikipedia_url, observations_count,
    overview, traits, care_params
  ) VALUES (
    @name_cn, @name_latin, @common_name_en, @family, @genus,
    @distribution, @habitat, @conservation, @reproduction, @etymology,
    @image_url, @image_attribution, @image_license,
    @wikipedia_url, @observations_count,
    @overview, @traits, @care_params
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
    observations_count = COALESCE(excluded.observations_count, species.observations_count)
`);

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
    });

    if (existing) updated++; else inserted++;
  }
});

insertAll();

// 显示结果
console.log(`\n📥 入库完成: 新增 ${inserted} / 更新 ${updated}`);
console.log(`   数据源: GBIF + iNaturalist + Reptile Database\n`);

// 验证
const all = db.prepare(`
  SELECT species_id, name_cn, name_latin, family, distribution, habitat, image_url
  FROM species ORDER BY species_id
`).all();

for (const s of all) {
  const hasImg = s.image_url ? '🖼' : '✗';
  const dist = (s.distribution || '').slice(0, 40);
  const hab = (s.habitat || '').slice(0, 30);
  console.log(`  ${s.species_id} | ${s.name_cn} | ${s.family || '?'} | ${dist} | ${hab} | ${hasImg}`);
}

console.log(`\n  总计: ${all.length} 个品种`);
db.close();
