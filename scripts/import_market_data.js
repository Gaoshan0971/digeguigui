#!/usr/bin/env node
/**
 * TTS/BW 爬虫数据导入脚本
 * 将 TheTurtleSource + Backwater Reptiles 爬取数据匹配到 species 表，更新图片和价格
 * 
 * 用法: node scripts/import_market_data.js
 */

const path = require('path');
const fs = require('fs');
const Database = require(path.join(__dirname, '..', 'server', 'node_modules', 'better-sqlite3'));

const DB_PATH = path.join(__dirname, '..', 'data', 'digeguigui.db');
const TTS_FILE = path.join(__dirname, '..', 'data', 'tts_products.json');
const BW_FILE = path.join(__dirname, '..', 'data', 'bw_products.json');
const CARE_FILE = path.join(__dirname, '..', 'data', 'tts_care_sheets.json');

// ── 学名映射 ──────────────────────────────────
// 将 TTS/BW 的英文俗名映射到 species 表的 name_latin
// TTS 没有学名，需要通过英文名推断
const NAME_MAP = {
  // Turtles - common species
  'common snapping turtle': 'Chelydra serpentina',
  'albino common snapping turtle': 'Chelydra serpentina',
  'hypo melanistic common snapping turtle': 'Chelydra serpentina',
  'heterozygous for albinos common snappers': 'Chelydra serpentina',
  'mississippi map turtle': 'Graptemys pseudogeographica kohnii',
  'ringed map turtle': 'Graptemys oculifera',
  'yellow-blotched map turtle': 'Graptemys flavimaculata',
  'three-striped mud turtle': 'Kinosternon baurii',
  'white-lipped mud turtle': 'Kinosternon leucostomum',
  'mississippi mud turtle': 'Kinosternon subrubrum hippocrepis',
  'musk turtle': 'Sternotherus odoratus',
  'razorback musk turtle': 'Sternotherus carinatus',
  'florida chicken turtle': 'Deirochelys reticularia chrysea',
  'painted river terrapin': 'Batagur borneoensis',
  'african dwarf mud turtle': 'Pelusios nanus',
  'gibba side-necked turtle': 'Mesoclemmys gibba',
  'madagascar big-headed side-necked turtles': 'Erymnochelys madagascariensis',
  'albino pink belly side-necked turtle': 'Emydura subglobosa',
  'asian yellow pond turtle': 'Mauremys mutica',
  'chinese golden box turtle': 'Cuora flavomarginata',
  'cohilan box turtle': 'Terrapene coahuila',
  'kwangtung river turtle': 'Mauremys nigricans',
  'giant asian leaf pond turtle': 'Heosemys grandis',
  
  // Sliders and cooters
  'red-eared slider': 'Trachemys scripta elegans',
  'albino red-eared slider': 'Trachemys scripta elegans',
  'leucistic albino red-eared slider': 'Trachemys scripta elegans',
  'melanistic red-eared slider': 'Trachemys scripta elegans',
  'charcoal red-eared slider': 'Trachemys scripta elegans',
  'hypo translucent albino red-eared slider': 'Trachemys scripta elegans',
  'paradox albino': 'Trachemys scripta elegans',
  'paradox albino red-eared slider': 'Trachemys scripta elegans',
  'emerald albino paradox red-eared slider': 'Trachemys scripta elegans',
  'red-eared slider heterozygous for albino': 'Trachemys scripta elegans',
  'yellow-bellied slider': 'Trachemys scripta scripta',
  'yellow-bellied sliders heterozygous for albino': 'Trachemys scripta scripta',
  'cumberland slider': 'Trachemys scripta troostii',
  'florida red-bellied turtle': 'Pseudemys nelsoni',
  'golden flame florida red-bellied turtle': 'Pseudemys nelsoni',
  't-positive albino florida red belly': 'Pseudemys nelsoni',
  'southern river cooter': 'Pseudemys concinna concinna',
  'peninsula cooter': 'Pseudemys peninsularis',
  'hieroglyphic river cooter': 'Pseudemys concinna hieroglyphica',
  'nicaraguan slider': 'Trachemys emolli',
  'rio grande slider': 'Trachemys gaigeae',
  'guatemalan ornate slider': 'Trachemys venusta',
  'mexican ornate slider': 'Trachemys ornata',
  'hybrid rio grande red eared mexican ornate': 'Trachemys hybrid',
  
  // Map turtles
  'black-knobbed map turtle': 'Graptemys nigrinoda',
  'pearl river map turtle': 'Graptemys pearlensis',
  
  // Box turtles
  'eastern box turtle': 'Terrapene carolina carolina',
  'three-toed box turtle': 'Terrapene carolina triunguis',
  'ornate box turtle': 'Terrapene ornata',
  'chinese box turtle': 'Cuora flavomarginata',
  'indonesian box turtle': 'Cuora amboinensis',
  'florida box turtle': 'Terrapene carolina bauri',
  'gulf coast box turtle': 'Terrapene carolina major',
  
  // Wood turtles
  'north american wood turtle': 'Glyptemys insculpta',
  'central american ornate wood turtle': 'Rhinoclemmys pulcherrima manni',
  'maracaibo wood turtle': 'Rhinoclemmys diademata',
  'mexican red wood turtle': 'Rhinoclemmys rubida',
  'black wood turtle': 'Rhinoclemmys funerea',
  'furrowed wood turtle': 'Rhinoclemmys areolata',
  'painted wood turtle': 'Rhinoclemmys pulcherrima',
  'japanese wood turtle': 'Mauremys japonica',
  'malayan wood turtle': 'Heosemys spinosa',
  
  // Painted turtles
  'eastern painted turtle': 'Chrysemys picta picta',
  'western painted turtle': 'Chrysemys picta bellii',
  'southern painted turtle': 'Chrysemys picta dorsalis',
  
  // Sideneck turtles
  'african hinge sideneck turtle': 'Pelusios castaneus',
  'peters sideneck turtle': 'Pelusios subniger',
  'pink-bellied sideneck turtle': 'Emydura subglobosa',
  'new guinea sideneck turtle': 'Emydura subglobosa',
  
  // Other turtles
  'spotted turtle': 'Clemmys guttata',
  'blandings turtle': 'Emydoidea blandingii',
  'european pond turtle': 'Emys orbicularis',
  'japanese pond turtle': 'Mauremys japonica',
  'reeves turtle': 'Mauremys reevesii',
  'golden thread turtle': 'Mauremys sinensis',
  'asian leaf turtle': 'Cyclemys dentata',
  'mata mata turtle': 'Chelus fimbriatus',
  'twist-necked turtle': 'Platemys platycephala',
  'reimanns snakeneck turtle': 'Chelodina reimanni',
  'gibba turtle': 'Mesoclemmys gibba',
  'spiny softshell turtle': 'Apalone spinifera',
  'florida softshell turtle': 'Apalone ferox',
  'florida snapping turtle': 'Chelydra serpentina osceola',
  'albino snapping turtle': 'Chelydra serpentina',
  
  // Tortoises
  'sulcata tortoise': 'Centrochelys sulcata',
  'patterened sulcata tortoises': 'Centrochelys sulcata',
  'sulcata tortoise adult': 'Centrochelys sulcata',
  'leopard tortoise': 'Stigmochelys pardalis',
  'red-footed tortoise': 'Chelonoidis carbonarius',
  'bolivian cherry-headed red-footed tortoise': 'Chelonoidis carbonarius',
  'platinum yellow leucistic red-foot tortoise': 'Chelonoidis carbonarius',
  'greek tortoise': 'Testudo graeca',
  'hermanns tortoise': 'Testudo hermanni',
  'elongated tortoise': 'Indotestudo elongata',
  'aldabra tortoise': 'Aldabrachelys gigantea',
  
  // BW additional
  'mexican ornate slider turtle': 'Trachemys ornata',
  'pearl river map turtle': 'Graptemys pearlensis',
};

function matchSpecies(name, db) {
  // Direct name map lookup
  const key = name.toLowerCase().trim();
  
  // Try exact match
  for (const [english, latin] of Object.entries(NAME_MAP)) {
    if (key.includes(english) || english.includes(key)) {
      return latin;
    }
  }
  
  // Try DB fuzzy match
  const words = key.split(/[\s-]+/).filter(w => w.length > 2);
  if (words.length >= 2) {
    const stmt = db.prepare('SELECT name_latin, name_cn FROM species WHERE name_latin LIKE ? OR name_cn LIKE ? LIMIT 1');
    for (const word of words.slice(-2)) {  // last 2 key words
      const row = stmt.get(`%${word}%`, `%${word}%`);
      if (row) return row.name_latin;
    }
  }
  
  return null;
}

function importTTS(db) {
  if (!fs.existsSync(TTS_FILE)) {
    console.log('⚠️  TTS data file not found, skipping');
    return;
  }
  
  const products = JSON.parse(fs.readFileSync(TTS_FILE, 'utf8'));
  console.log(`📦 Importing ${products.length} TTS products...`);
  
  let matched = 0, unmatched = 0, updated = 0;
  
  const updateStmt = db.prepare(`
    UPDATE species 
    SET image_url = CASE WHEN image_url IS NULL OR image_url = '' THEN ? ELSE image_url END,
        image_attribution = 'TheTurtleSource.com',
        image_license = 'Fair Use - product photo',
        market_data = json_set(
          COALESCE(market_data, '{}'),
          '$.tts_url', ?,
          '$.tts_price', ?
        )
    WHERE name_latin LIKE ? || '%'
  `);
  
  for (const prod of products) {
    if (!prod.name) {
      unmatched++;
      continue;
    }
    
    const latin = matchSpecies(prod.name, db);
    if (!latin) {
      unmatched++;
      if (unmatched <= 10) console.log(`  ❓ Unmatched: ${prod.name}`);
      continue;
    }
    
    matched++;
    const image = prod.images && prod.images.length > 0 ? prod.images[0] : null;
    const price = prod.price ? JSON.stringify(prod.price) : null;
    
    const result = updateStmt.run(image, prod.url, price, latin);
    if (result.changes > 0) updated++;
  }
  
  console.log(`  ✅ ${matched} matched, ${unmatched} unmatched, ${updated} species updated`);
  
  // Also handle morph products (don't update species, but log)
  const morphProducts = products.filter(p => p.morph_tags && p.morph_tags.length > 0);
  console.log(`  🧬 ${morphProducts.length} morph products found`);
  
  return { matched, unmatched, updated, morphs: morphProducts };
}

function importBW(db) {
  if (!fs.existsSync(BW_FILE)) {
    console.log('⚠️  BW data file not found, skipping');
    return;
  }
  
  const products = JSON.parse(fs.readFileSync(BW_FILE, 'utf8'));
  console.log(`📦 Importing ${products.length} BW products...`);
  
  let matched = 0, unmatched = 0, updated = 0;
  
  const updateStmt = db.prepare(`
    UPDATE species 
    SET image_url = CASE WHEN image_url IS NULL OR image_url = '' THEN ? ELSE image_url END,
        image_attribution = CASE WHEN image_url IS NULL OR image_url = '' THEN 'BackwaterReptiles.com' ELSE image_attribution END,
        image_license = CASE WHEN image_url IS NULL OR image_url = '' THEN 'Fair Use - product photo' ELSE image_license END,
        market_data = json_set(
          COALESCE(market_data, '{}'),
          '$.bw_url', ?,
          '$.bw_price', ?
        )
    WHERE name_latin LIKE ? || '%'
  `);
  
  for (const prod of products) {
    if (!prod.name) {
      unmatched++;
      continue;
    }
    
    const latin = matchSpecies(prod.name, db);
    if (!latin) {
      unmatched++;
      continue;
    }
    
    matched++;
    const result = updateStmt.run(prod.image, prod.url, prod.price_usd, latin);
    if (result.changes > 0) updated++;
  }
  
  console.log(`  ✅ ${matched} matched, ${unmatched} unmatched, ${updated} species updated`);
  return { matched, unmatched, updated };
}

function importCareSheets(db) {
  if (!fs.existsSync(CARE_FILE)) {
    console.log('⚠️  Care sheets file not found, skipping');
    return;
  }
  
  const sheets = JSON.parse(fs.readFileSync(CARE_FILE, 'utf8'));
  console.log(`📋 Importing ${sheets.length} care sheets...`);
  
  // Store care sheets in a JSON column or reference
  // For now, store as json in market_data
  for (const sheet of sheets) {
    if (!sheet.title || !sheet.body || sheet.body.length === 0) continue;
    
    // Map care sheet title to species group
    const titleLower = sheet.title.toLowerCase();
    let familyMatch = null;
    
    if (titleLower.includes('mud') || titleLower.includes('musk')) familyMatch = 'Kinosternidae';
    else if (titleLower.includes('map')) familyMatch = 'Emydidae';
    else if (titleLower.includes('painted')) familyMatch = 'Emydidae';
    else if (titleLower.includes('slider') || titleLower.includes('cooter')) familyMatch = 'Emydidae';
    else if (titleLower.includes('snapping')) familyMatch = 'Chelydridae';
    else if (titleLower.includes('soft')) familyMatch = 'Trionychidae';
    else if (titleLower.includes('box')) familyMatch = 'Emydidae';
    else if (titleLower.includes('blanding')) familyMatch = 'Emydidae';
    else if (titleLower.includes('spotted') || titleLower.includes('wood') || titleLower.includes('bog') || titleLower.includes('pond')) familyMatch = 'Emydidae';
    else if (titleLower.includes('chicken')) familyMatch = 'Emydidae';
    else if (titleLower.includes('diamondback')) familyMatch = 'Emydidae';
    else if (titleLower.includes('tortoise') || titleLower.includes('footed') || titleLower.includes('spurred')) familyMatch = 'Testudinidae';
    else if (titleLower.includes('vietnamese')) familyMatch = 'Geoemydidae';
    else if (titleLower.includes('matamata')) familyMatch = 'Chelidae';
    
    if (familyMatch) {
      // Update all species in this family with care sheet reference
      const bodyText = sheet.body.slice(0, 5).join('\n');  // first 5 paragraphs
      db.prepare(`
        UPDATE species 
        SET market_data = json_set(
          COALESCE(market_data, '{}'),
          '$.tts_care_sheet', json_object('title', ?, 'url', ?, 'content_preview', ?)
        )
        WHERE class_name = 'Reptilia' AND family = ?
      `).run(sheet.title, sheet.url, bodyText, familyMatch);
    }
  }
  
  console.log(`  ✅ Care sheets linked to species by family`);
}

function main() {
  const db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');
  
  console.log('🦎 Importing market data to digeguigui DB...\n');
  
  // Enable JSON columns if needed
  try {
    db.exec(`ALTER TABLE species ADD COLUMN market_data TEXT DEFAULT '{}'`);
    console.log('  ✅ Added market_data column');
  } catch (e) {
    // Column already exists
  }
  
  const ttsResult = importTTS(db);
  console.log('');
  const bwResult = importBW(db);
  console.log('');
  importCareSheets(db);
  
  // Summary
  console.log('\n📊 Import Summary:');
  console.log(`  TTS: ${ttsResult?.matched || 0} species updated, ${ttsResult?.morphs?.length || 0} morph products`);
  console.log(`  BW:  ${bwResult?.matched || 0} species updated`);
  
  // Show species with new market data
  const withMarket = db.prepare(`
    SELECT name_cn, name_latin, 
           json_extract(market_data, '$.tts_price') as tts_price,
           json_extract(market_data, '$.bw_price') as bw_price
    FROM species 
    WHERE market_data IS NOT NULL AND market_data != '{}'
    ORDER BY name_cn
    LIMIT 20
  `).all();
  
  console.log(`\n  ${db.prepare("SELECT COUNT(*) FROM species WHERE market_data IS NOT NULL AND market_data != '{}'").get()['COUNT(*)']} species now have market data`);
  if (withMarket.length > 0) {
    console.log('  Sample:');
    for (const s of withMarket) {
      const parts = [];
      if (s.tts_price) parts.push(`TTS:$${JSON.parse(s.tts_price).min || '?'}`);
      if (s.bw_price) parts.push(`BW:$${s.bw_price}`);
      if (parts.length > 0) console.log(`    ${s.name_cn || s.name_latin}: ${parts.join(' | ')}`);
    }
  }
  
  db.close();
}

main();
