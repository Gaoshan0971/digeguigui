// seed_species.js — 龟种种子数据入库
const db = require('../server/db');
const species = require('../data/seed_species.json');

let inserted = 0;
let skipped = 0;

const insert = db.prepare(`
  INSERT OR IGNORE INTO species (name_cn, name_latin, family, difficulty, overview, traits, care_params)
  VALUES (?, ?, ?, ?, ?, ?, ?)
`);

const insertMany = db.transaction((items) => {
  for (const s of items) {
    const existing = db.prepare('SELECT species_id FROM species WHERE name_cn = ?').get(s.name_cn);
    if (existing) {
      console.log(`  ⏭ 跳过已存在: ${s.name_cn}`);
      skipped++;
      continue;
    }
    insert.run(s.name_cn, s.name_latin, s.family, s.difficulty, s.overview,
      JSON.stringify(s.traits), JSON.stringify(s.care_params));
    console.log(`  ✓ 新增: ${s.name_cn} (${s.name_latin})`);
    inserted++;
  }
});

// Filter out the 小鳄龟 duplicate (same as existing 鳄龟)
const filtered = species.filter(s => s.name_cn !== '小鳄龟');
console.log(`准备插入 ${filtered.length} 个龟种...\n`);
insertMany(filtered);

const total = db.prepare('SELECT COUNT(*) as cnt FROM species').get().cnt;
console.log(`\n✅ 完成！新增 ${inserted} 种，跳过 ${skipped} 种，数据库共 ${total} 种`);
