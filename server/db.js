// db.js — SQLite 数据库初始化 + Schema
const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = path.join(__dirname, '..', 'data', 'digeguigui.db');

const db = new Database(DB_PATH);

// WAL 模式 — 并发读性能更好
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

// ==================== Schema ====================

db.exec(`
  -- 用户
  CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    openid TEXT UNIQUE NOT NULL,
    nickname TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    role TEXT DEFAULT 'hobbyist',       -- hobbyist | breeder | expert
    reputation INTEGER DEFAULT 0,
    appraisal_count INTEGER DEFAULT 0,
    ai_consistency INTEGER DEFAULT 0,    -- AI一致性 0-100
    appraiser_grade INTEGER DEFAULT 1,   -- 品鉴师等级 1-5
    city TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
  );

  -- 品种百科
  CREATE TABLE IF NOT EXISTS species (
    species_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_cn TEXT NOT NULL,
    name_latin TEXT NOT NULL,
    common_name_en TEXT DEFAULT '',
    family TEXT DEFAULT '',
    genus TEXT DEFAULT '',
    difficulty INTEGER DEFAULT 0,       -- 饲养难度 1-5
    overview TEXT DEFAULT '',
    distribution TEXT DEFAULT '',
    habitat TEXT DEFAULT '',
    conservation TEXT DEFAULT '',
    reproduction TEXT DEFAULT '',
    etymology TEXT DEFAULT '',
    traits TEXT DEFAULT '{}',           -- JSON: 识别特征
    care_params TEXT DEFAULT '{}',      -- JSON: 饲养参数
    image_url TEXT DEFAULT '',
    image_attribution TEXT DEFAULT '',
    image_license TEXT DEFAULT '',
    wikipedia_url TEXT DEFAULT '',
    observations_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime'))
  );

  -- 藏品
  CREATE TABLE IF NOT EXISTS collections (
    collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    species_id INTEGER NOT NULL,
    image_urls TEXT DEFAULT '[]',
    caption TEXT DEFAULT '',
    -- 品相维度打分 (0=未评)
    shell_score INTEGER DEFAULT 0,
    head_score INTEGER DEFAULT 0,
    color_score INTEGER DEFAULT 0,
    body_score INTEGER DEFAULT 0,
    health_score INTEGER DEFAULT 0,
    overall_grade TEXT DEFAULT '',      -- S/A+/A/B/C
    city TEXT DEFAULT '',
    is_showcase INTEGER DEFAULT 0,      -- 是否公开在展示墙
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (species_id) REFERENCES species(species_id)
  );

  -- 品相鉴赏（众包打分）
  CREATE TABLE IF NOT EXISTS appraisals (
    appraisal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    comment TEXT DEFAULT '',
    shell_score INTEGER DEFAULT 0,
    head_score INTEGER DEFAULT 0,
    color_score INTEGER DEFAULT 0,
    body_score INTEGER DEFAULT 0,
    health_score INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (collection_id) REFERENCES collections(collection_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
  );

  -- 血统 — 繁育配对
  CREATE TABLE IF NOT EXISTS breedings (
    breeding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    breeder_id INTEGER NOT NULL,
    sire_collection_id INTEGER,
    dam_collection_id INTEGER,
    pairing_date TEXT,
    offspring_count INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (breeder_id) REFERENCES users(user_id),
    FOREIGN KEY (sire_collection_id) REFERENCES collections(collection_id),
    FOREIGN KEY (dam_collection_id) REFERENCES collections(collection_id)
  );

  -- 血统 — 子代
  CREATE TABLE IF NOT EXISTS offspring (
    offspring_id INTEGER PRIMARY KEY AUTOINCREMENT,
    breeding_id INTEGER NOT NULL,
    collection_id INTEGER,              -- 如果子代已被收录为藏品
    description TEXT DEFAULT '',
    image_url TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (breeding_id) REFERENCES breedings(breeding_id),
    FOREIGN KEY (collection_id) REFERENCES collections(collection_id)
  );

  -- 点赞
  CREATE TABLE IF NOT EXISTS likes (
    like_id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL DEFAULT 'collection',  -- collection | appraisal
    target_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(target_type, target_id, user_id)
  );

  -- 数据集标注提交
  CREATE TABLE IF NOT EXISTS dataset_submissions (
    submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    species_name TEXT NOT NULL,
    species_id INTEGER,
    image_base64 TEXT NOT NULL,
    submitter_name TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',        -- pending | approved | rejected
    reviewer_notes TEXT DEFAULT '',
    reviewed_at TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (species_id) REFERENCES species(species_id)
  );

  -- 索引
  CREATE INDEX IF NOT EXISTS idx_collections_user ON collections(user_id);
  CREATE INDEX IF NOT EXISTS idx_collections_species ON collections(species_id);
  CREATE INDEX IF NOT EXISTS idx_collections_created ON collections(created_at DESC);
  CREATE INDEX IF NOT EXISTS idx_appraisals_collection ON appraisals(collection_id);
  CREATE INDEX IF NOT EXISTS idx_breedings_breeder ON breedings(breeder_id);
  CREATE INDEX IF NOT EXISTS idx_likes_target ON likes(target_type, target_id);
`);

// ==================== Migration: v2 扩字段 ====================
// 为已有数据库补充新列（忽略已存在的列）
const newColumns = [
  'common_name_en TEXT DEFAULT \'\'',
  'genus TEXT DEFAULT \'\'',
  'distribution TEXT DEFAULT \'\'',
  'habitat TEXT DEFAULT \'\'',
  'conservation TEXT DEFAULT \'\'',
  'reproduction TEXT DEFAULT \'\'',
  'etymology TEXT DEFAULT \'\'',
  'image_attribution TEXT DEFAULT \'\'',
  'image_license TEXT DEFAULT \'\'',
  'wikipedia_url TEXT DEFAULT \'\'',
  'observations_count INTEGER DEFAULT 0',
];
for (const col of newColumns) {
  const colName = col.split(' ')[0];
  try { db.exec(`ALTER TABLE species ADD COLUMN ${col}`); } catch (e) {
    // 列已存在，忽略
  }
}

// ==================== Migration: 品鉴标注训练数据 ====================
db.exec(`
  CREATE TABLE IF NOT EXISTS labeled_appraisals (
    label_id INTEGER PRIMARY KEY AUTOINCREMENT,
    species_id INTEGER NOT NULL,
    image_url TEXT NOT NULL,
    shell_score INTEGER NOT NULL CHECK(shell_score BETWEEN 1 AND 10),
    head_score INTEGER NOT NULL CHECK(head_score BETWEEN 1 AND 10),
    color_score INTEGER NOT NULL CHECK(color_score BETWEEN 1 AND 10),
    body_score INTEGER NOT NULL CHECK(body_score BETWEEN 1 AND 10),
    health_score INTEGER NOT NULL CHECK(health_score BETWEEN 1 AND 10),
    overall_grade TEXT NOT NULL,
    market_range TEXT DEFAULT '',
    comment TEXT DEFAULT '',
    labeled_by TEXT DEFAULT 'user',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (species_id) REFERENCES species(species_id)
  );
  CREATE INDEX IF NOT EXISTS idx_labels_species ON labeled_appraisals(species_id);
`)
console.log('[db] Labeling table ready');

// ==================== Migration: 识龟反馈训练数据 ====================

db.exec(`
  CREATE TABLE IF NOT EXISTS identify_feedback (
    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_token TEXT DEFAULT '',
    image_base64 TEXT NOT NULL,
    model_species_id INTEGER,
    model_confidence REAL DEFAULT 0,
    model_top3 TEXT DEFAULT '[]',
    engine TEXT DEFAULT '',
    user_species_id INTEGER,
    feedback_type TEXT NOT NULL CHECK(feedback_type IN ('confirmed','corrected','rejected')),
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (model_species_id) REFERENCES species(species_id),
    FOREIGN KEY (user_species_id) REFERENCES species(species_id)
  );
  CREATE INDEX IF NOT EXISTS idx_feedback_type ON identify_feedback(feedback_type);
  CREATE INDEX IF NOT EXISTS idx_feedback_user ON identify_feedback(user_token);
  CREATE INDEX IF NOT EXISTS idx_feedback_species ON identify_feedback(user_species_id);
`)
console.log('[db] Identify feedback table ready');

// ==================== Migration: 达人邀请码 ====================

db.exec(`
  CREATE TABLE IF NOT EXISTS invite_codes (
    code_id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    batch_id TEXT NOT NULL,
    created_by TEXT DEFAULT '',
    used_by TEXT DEFAULT '',
    used_at TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
  );
  CREATE INDEX IF NOT EXISTS idx_invite_code ON invite_codes(code);
  CREATE INDEX IF NOT EXISTS idx_invite_batch ON invite_codes(batch_id);
`)

// 批次元数据表
db.exec(`
  CREATE TABLE IF NOT EXISTS invite_batches (
    batch_id TEXT PRIMARY KEY,
    created_by TEXT DEFAULT '',
    total INTEGER DEFAULT 0,
    share_card_url TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
  )
`)
console.log('[db] Invite codes table ready');
console.log('[db] Invite codes table ready');

// ==================== Migration: Provenance v1 ====================
const fs = require('fs');
const provPath = path.join(__dirname, '..', 'data', 'provenance_schema.sql');
if (fs.existsSync(provPath)) {
  db.exec(fs.readFileSync(provPath, 'utf-8'));
  console.log('[db] Provenance tables ready');
}

module.exports = db;
