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
    city TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
  );

  -- 品种百科
  CREATE TABLE IF NOT EXISTS species (
    species_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_cn TEXT NOT NULL,
    name_latin TEXT NOT NULL,
    family TEXT DEFAULT '',
    difficulty INTEGER DEFAULT 0,       -- 饲养难度 1-5
    overview TEXT DEFAULT '',
    traits TEXT DEFAULT '{}',           -- JSON: 识别特征
    care_params TEXT DEFAULT '{}',      -- JSON: 饲养参数
    image_url TEXT DEFAULT '',
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

module.exports = db;
