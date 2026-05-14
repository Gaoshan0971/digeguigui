-- Provenance 系统迁移 v1.0
-- 爬宠出生证明 + 所有权转移 + 成长事件 + 生物特征库

-- 繁育者认证
CREATE TABLE IF NOT EXISTS breeders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id),

    -- 实名认证
    real_name TEXT NOT NULL,
    id_card_hash TEXT NOT NULL,           -- SHA256(姓名+身份证号)，不存明文
    id_card_photo TEXT,                   -- 身份证照片 COS URL
    phone TEXT,

    -- 场地信息
    facility_name TEXT,                   -- 场地名称
    facility_address TEXT,                -- 地址
    facility_gps_lat REAL,                -- 场地纬度
    facility_gps_lng REAL,                -- 场地经度
    facility_photos TEXT,                 -- 场地照片 JSON Array

    -- 资质
    certified_species TEXT,               -- 认证品种 JSON: [452, 82, 204]
    cert_status TEXT DEFAULT 'pending',   -- pending | approved | rejected
    cert_level TEXT DEFAULT 'basic',      -- basic(免费) | advanced(¥99/年) | master(邀请制)
    cert_reviewed_at TEXT,                -- 审核时间

    -- 信誉系统
    reputation_score INTEGER DEFAULT 100, -- 初始 100，违规扣分
    total_births INTEGER DEFAULT 0,       -- 总出生登记数
    total_transfers INTEGER DEFAULT 0,    -- 总转移数
    dispute_count INTEGER DEFAULT 0,      -- 争议数

    -- 密码学
    public_key TEXT,                      -- 繁育者公钥 (ed25519)
    signing_key_salt TEXT,                -- 私钥加密盐

    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 出生锚定（一只龟一辈子一条）
CREATE TABLE IF NOT EXISTS provenance_anchors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anchor_id TEXT UNIQUE NOT NULL,       -- DGG-T-XXXXX (公开锚定号)

    -- 身份
    breeder_id INTEGER REFERENCES breeders(id),
    species_id INTEGER REFERENCES species(species_id),
    individual_name TEXT,                 -- 个体编号 (繁育者自定义)
    sex TEXT,                             -- male | female | unknown

    -- 出生信息
    birth_date TEXT NOT NULL,             -- ISO 8601
    birth_gps_lat REAL,                   -- 出生地 GPS
    birth_gps_lng REAL,
    clutch_id TEXT,                       -- 窝次编号

    -- 血统
    parent_male_anchor TEXT,              -- 父本锚定ID
    parent_female_anchor TEXT,            -- 母本锚定ID

    -- 出生快照
    birth_photos TEXT NOT NULL,           -- 出生照片 JSON Array
    biometric_hash TEXT NOT NULL,         -- 生物特征哈希: SHA256(feature_vector)
    biometric_model TEXT,                 -- 特征提取模型: resnet50_v1
    feature_dim INTEGER,                  -- 特征向量维度

    -- Git 锚定 (出生一次，不可变)
    git_commit_hash TEXT NOT NULL,        -- Git commit SHA
    json_file_path TEXT,                  -- data/provenance/<anchor_id>.json

    -- 状态
    status TEXT DEFAULT 'active',         -- active | transferred | deceased
    metadata TEXT,                        -- JSON 扩展字段

    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_anchors_breeder ON provenance_anchors(breeder_id);
CREATE INDEX IF NOT EXISTS idx_anchors_species ON provenance_anchors(species_id);
CREATE INDEX IF NOT EXISTS idx_anchors_parent ON provenance_anchors(parent_male_anchor, parent_female_anchor);

-- 所有权转移（SQLite 内哈希链）
CREATE TABLE IF NOT EXISTS provenance_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anchor_id TEXT NOT NULL REFERENCES provenance_anchors(anchor_id),

    -- 交易双方
    from_user_id INTEGER REFERENCES users(user_id),
    to_user_id INTEGER REFERENCES users(user_id),
    transfer_type TEXT,                   -- sale | gift | loan | exhibition

    -- 转移时验证
    transfer_date TEXT NOT NULL,
    verification_photo TEXT,              -- 交接时照片
    biometric_match_score REAL,           -- 与出生锚定的 AI 匹配分 (0-1)

    -- 价格
    price REAL,                           -- 成交价 (可选)
    currency TEXT DEFAULT 'CNY',

    -- SQLite 内哈希链
    transfer_hash TEXT,                   -- SHA256(prev_hash || transfer_data)
    prev_hash TEXT,                       -- 出生 Git commit 或上笔转移 hash

    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_transfers_anchor ON provenance_transfers(anchor_id);

-- 成长事件 / 历任主人备注
CREATE TABLE IF NOT EXISTS provenance_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anchor_id TEXT NOT NULL REFERENCES provenance_anchors(anchor_id),

    -- 记录者（繁育者 / 历任主人，NULL=系统自动）
    owner_id INTEGER REFERENCES users(user_id),

    event_type TEXT NOT NULL,             -- health_check | measurement | shedding | feeding | behavior | environment | note | photo | milestone
    event_date TEXT NOT NULL,
    description TEXT,                     -- 自由备注：喂食习惯、环境变化、性格等

    -- 测量数据
    weight REAL,                          -- 克
    length_cm REAL,                       -- 厘米

    -- 成长照片 + 特征验证
    event_photo TEXT,
    biometric_hash TEXT,
    biometric_match_score REAL,           -- 与上一次的匹配分

    -- SQLite 内哈希链
    event_hash TEXT,                      -- SHA256(prev_hash || event_data)
    prev_hash TEXT,                       -- 链接到上一事件或出生Git commit

    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_events_anchor ON provenance_events(anchor_id);
CREATE INDEX IF NOT EXISTS idx_events_owner ON provenance_events(owner_id);

-- 生物特征模板库（AI 特征向量存储）
CREATE TABLE IF NOT EXISTS biometric_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anchor_id TEXT NOT NULL REFERENCES provenance_anchors(anchor_id),
    species_id INTEGER REFERENCES species(species_id),
    template_version TEXT NOT NULL,       -- 特征提取器版本
    feature_vector BLOB NOT NULL,         -- 特征向量 (序列化)
    feature_dim INTEGER,                  -- 向量维度 (如 2048)
    image_url TEXT NOT NULL,              -- 源图片 URL
    region TEXT,                          -- carapace | plastron | head | overall
    quality_score REAL,                   -- 图片质量分
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_bio_anchor ON biometric_templates(anchor_id);
CREATE INDEX IF NOT EXISTS idx_bio_match ON biometric_templates(species_id, template_version);

-- 支付订单
CREATE TABLE IF NOT EXISTS payment_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    out_trade_no TEXT UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(user_id),
    product_type TEXT NOT NULL,           -- appraise | anchor_50 | anchor_100 | anchor_daily | breeder_cert
    product_id TEXT DEFAULT '',
    total_fee INTEGER NOT NULL,           -- 分
    status TEXT DEFAULT 'pending',        -- pending | paid | refunded | closed
    transaction_id TEXT,                  -- 微信支付交易号
    paid_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_payment_user ON payment_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_out ON payment_orders(out_trade_no);
