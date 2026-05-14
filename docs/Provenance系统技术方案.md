# 🐢 滴个龟龟 Provenance 系统 — 爬宠出生证明技术方案

> v1.1 | 2026-05-14  
> Owner: Hermes (代表滴个龟龟项目)

---

## 一、为什么 Provenance 是终局之战

爬宠行业有一个所有平台都回避的致命痛点：

```
买家：这是 CB（人工繁育）的吗？
卖家：是的亲，有证。
买家：证能保证是真的吗？
卖家：……
买家：万一 WC（野生）我被抓了怎么办？
卖家：亲你再看看别的？
```

| 维度 | 现状 | 后果 |
|------|------|------|
| **合法性问题** | CITES 附录物种：CB 合法，WC 刑事。国内重点保护：人工可养，野生进去 | 买家永远活在恐惧中 |
| **价格造假** | WC 冒充 CB 差价 5-10 倍（黄缘闭壳龟 WC ¥200 → CB ¥2000+） | 市场信任崩塌 |
| **执法困境** | 执法部门没有技术手段区分 CB/WC，只能靠口供和纸质证 | 冤案或漏网 |
| **血统造假** | "这窝是 Super Pastel x Mojave 的"——全是嘴说 | 繁育者信誉无法建立 |

**谁解决了 CB/WC 的技术验证，谁就掌握了这个行业的基础设施定价权。**

滴个龟龟已经有了品系基因库（170基因 + 192组合 + 331价格），现在唯一缺的就是 **来源证明层**——这是估值、信任、合规三者的基石。

---

## 二、核心概念：爬宠出生证明（Provenance Anchor）

### 2.1 一句话定义

**在幼体出壳/出生的那一刻，用密码学手段将"时间 + 地点 + 生物特征 + 繁育者身份"锚定为一串不可篡改的哈希，形成这只爬宠终身的数字身份证。**

### 2.2 为什么出生时刻是关键

- **WC 个体不存在出生时刻的锚定记录**——这本身就是 CB 的铁证
- **后补出生证明不可行**——AI 幼体特征检测（尺寸/卵齿/卵黄囊残留）+ Git commit 时间戳，三重验证
- **壳纹/头纹是天然指纹**——每只龟的背甲盾片排列天生独一无二，出生时拍照 + AI 提取特征向量 = 终身可验证
- **历任主人都可追加备注**——喂食习惯、环境变化、性格观察，每任主人往时间线上加一笔，完整生命史不可篡改

---

## 三、系统架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                    滴个龟龟 Provenance 系统                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│  │ 繁育者终端    │    │ 买家终端      │    │ 执法终端      │         │
│  │ (小程序)      │    │ (小程序/H5)   │    │ (专用 API)    │         │
│  │              │    │              │    │              │         │
│  │ ①注册认证    │    │ ②扫码验证    │    │ ③司法鉴定    │         │
│  │ 出生登记     │    │ 转移确认     │    │ 批量比对     │         │
│  │ 窝次管理     │    │ 溯源查看     │    │ 来源判定     │         │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘         │
│         │                   │                   │                 │
│         └───────────────────┼───────────────────┘                 │
│                             │                                     │
│                    ┌────────▼────────┐                            │
│                    │   API Gateway    │                            │
│                    │  api.digeguigui  │                            │
│                    └────────┬────────┘                            │
│                             │                                     │
│         ┌───────────────────┼───────────────────┐                 │
│         │                   │                   │                 │
│  ┌──────▼──────┐   ┌───────▼───────┐   ┌───────▼──────┐          │
│  │ 业务服务     │   │ AI 识别引擎    │   │ 链上锚定      │          │
│  │             │   │               │   │              │          │
│  │ 繁育者认证  │   │ 龟纹特征提取   │   │ 哈希链生成   │          │
│  │ 出生登记    │   │ 1:1 验证比对   │   │ 区块链公证   │          │
│  │ 转移记录    │   │ 1:N 搜索匹配   │   │ 时间戳服务   │          │
│  │ 血统追溯    │   │ 模型持续迭代   │   │ 数字签名     │          │
│  └──────┬──────┘   └───────┬───────┘   └───────┬──────┘          │
│         │                   │                   │                 │
│  ┌──────▼───────────────────▼───────────────────▼──────┐          │
│  │                    SQLite 数据库                       │          │
│  │  breeders | anchors | transfers | events | bio_templates │      │
│  └──────────────────────────────────────────────────────┘          │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 四、数据库设计

### 4.1 繁育者认证表 (breeders)

```sql
CREATE TABLE breeders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),

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

    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
```

### 4.2 出生锚定表 (provenance_anchors)

```sql
CREATE TABLE provenance_anchors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anchor_id TEXT UNIQUE NOT NULL,       -- DGG-T-XXXXXX (公开锚定号)

    -- 身份
    breeder_id INTEGER REFERENCES breeders(id),
    species_id INTEGER REFERENCES species(id),
    individual_name TEXT,                 -- 个体编号 (繁育者自定义)
    sex TEXT,                             -- male | female | unknown

    -- 出生信息
    birth_date TEXT NOT NULL,             -- ISO 8601
    birth_gps_lat REAL,                   -- 出生地 GPS
    birth_gps_lng REAL,
    clutch_id TEXT,                       -- 窝次编号

    -- 血统
    parent_male_anchor TEXT,              -- 父本锚定ID (可自引用)
    parent_female_anchor TEXT,            -- 母本锚定ID

    -- 出生快照
    birth_photos TEXT NOT NULL,           -- 出生照片 JSON Array (COS URLs)
    biometric_hash TEXT NOT NULL,         -- 生物特征哈希: SHA256(feature_vector)
    biometric_model TEXT,                 -- 特征提取模型: resnet50_v1 | efficientnet_b3_v1

    -- 链上证据
    prov_hash TEXT NOT NULL,              -- 链上哈希: SHA256(prev_hash + anchor_data)
    prev_hash TEXT,                       -- 前一锚定哈希 (窝次内)
    timestamp_signature TEXT,             -- 第三方时间戳签名 (RFC 3161)
    breeder_signature TEXT,               -- 繁育者数字签名

    -- 状态
    status TEXT DEFAULT 'active',         -- active | transferred | deceased
    metadata TEXT,                        -- JSON 扩展字段

    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_anchors_breeder ON provenance_anchors(breeder_id);
CREATE INDEX idx_anchors_species ON provenance_anchors(species_id);
CREATE INDEX idx_anchors_parent ON provenance_anchors(parent_male_anchor, parent_female_anchor);
```

### 4.3 所有权转移表 (provenance_transfers)

```sql
CREATE TABLE provenance_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anchor_id TEXT NOT NULL REFERENCES provenance_anchors(anchor_id),

    -- 交易双方
    from_user_id INTEGER REFERENCES users(id),
    to_user_id INTEGER REFERENCES users(id),
    transfer_type TEXT,                   -- sale | gift | loan | exhibition

    -- 转移时验证
    transfer_date TEXT NOT NULL,
    verification_photo TEXT,              -- 交接时照片
    biometric_match_score REAL,           -- 与出生锚定的 AI 匹配分 (0-1)

    -- 价格
    price REAL,                           -- 成交价 (可选)
    currency TEXT DEFAULT 'CNY',

    -- 链上
    transfer_hash TEXT,                   -- SHA256(prev_transfer_hash + transfer_data)
    prev_transfer_hash TEXT,
    breeder_signature TEXT,

    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_transfers_anchor ON provenance_transfers(anchor_id);
```

### 4.4 成长事件表 (provenance_events)

```sql
CREATE TABLE provenance_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anchor_id TEXT NOT NULL REFERENCES provenance_anchors(anchor_id),

    -- 记录者（繁育者 / 历任主人）
    owner_id INTEGER REFERENCES users(id),  -- NULL=系统自动（如AI匹配记录）

    event_type TEXT NOT NULL,             -- health_check | measurement | shedding | feeding | behavior | environment | note | photo | milestone
    event_date TEXT NOT NULL,
    description TEXT,                     -- 自由备注：喂食习惯、环境变化、性格等

    -- 测量数据
    weight REAL,                          -- 克
    length_cm REAL,                       -- 厘米

    -- 成长照片 + 特征验证
    event_photo TEXT,
    biometric_hash TEXT,
    biometric_match_score REAL,           -- 与上一次的匹配分 (检测生长变化)

    -- 链上
    event_hash TEXT,                      -- SHA256(prev_event_hash || event_data)
    prev_event_hash TEXT,

    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_events_anchor ON provenance_events(anchor_id);
CREATE INDEX idx_events_owner ON provenance_events(owner_id);
```

### 4.5 生物特征模板表 (biometric_templates)

```sql
CREATE TABLE biometric_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anchor_id TEXT NOT NULL REFERENCES provenance_anchors(anchor_id),
    species_id INTEGER REFERENCES species(id),
    template_version TEXT NOT NULL,       -- 特征提取器版本
    feature_vector BLOB NOT NULL,         -- 特征向量 (numpy array 序列化)
    feature_dim INTEGER,                  -- 向量维度 (如 512 / 1280)
    image_url TEXT NOT NULL,              -- 源图片 URL
    region TEXT,                          -- carapace | plastron | head | overall
    quality_score REAL,                   -- 图片质量分 (用于过滤低质量模板)
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_bio_anchor ON biometric_templates(anchor_id);
CREATE INDEX idx_bio_match ON biometric_templates(species_id, template_version);
```

---

## 五、链上锚定方案

### 5.1 方案对比

| 方案 | 成本 | 公信力 | 合规性 | 维护 | 推荐 |
|------|------|--------|--------|------|------|
| **自建哈希链 + 时间戳** | 💰 零 | ⭐⭐⭐ | ✅ 完全自主 | 低 | ✅ **MVP首选** |
| FISCO BCOS (微众银行) | 💰 自建节点 | ⭐⭐⭐⭐ | ✅ 国密支持 | 中 | 进阶 |
| 长安链 ChainMaker | 💰 自建节点 | ⭐⭐⭐⭐⭐ | ✅ 国家背书 | 高 | 商业化后 |
| 蚂蚁链版权保护 | 💰💰 按次收费 | ⭐⭐⭐⭐ | ✅ | 低 | 看性价比 |
| 以太坊/BSC | 💰 Gas费 | ⭐⭐⭐⭐ | ⚠️ 灰色地带 | 低 | ❌ 国内不推荐 |

### 5.2 MVP 方案：自建双链哈希 + 联合信任时间戳

```
锚定流程：

1. 出生登记请求
   ├── 繁育者提交：照片 + GPS + 品种 + 个体信息
   └── 服务器端：
       ├── AI 提取生物特征 → feature_vector → SHA256 = biometric_hash
       ├── 调用联合信任时间戳服务 → RFC 3161 timestamp token
       ├── 计算 prov_hash = SHA256(prev_anchor_hash || biometric_hash || timestamp || gps || breeder_id)
       ├── 繁育者私钥签名 prov_hash
       └── 存储完整记录到 SQLite

2. 公开锚定（不需要公链）
   ├── 将 prov_hash 发布到公开位置：
   │   ├── 滴个龟龟官网透明度页面 (transparency.digeguigui.com/anchors)
   │   ├── 滴个龟龟公众号定期发布 Merkle Root
   │   └── （可选）发布到 Gitee 仓库的公开文件
   └── 任何第三方可以验证：prov_hash = SHA256(已知数据) ✓

3. 转移链
   ├── transfer_hash = SHA256(prev_transfer_hash || new_owner || timestamp)
   └── 链状结构不可逆追加
```

### 5.3 为什么自建就够了

- **哈希函数是公开的**：任何人拿原始数据都能验证 prov_hash，不需要链
- **公开锚定**：把哈希发布到多个公开位置 = 无法篡改（改了哈希就对不上）
- **时间戳服务**：联合信任（tsa.cn）是最高法院认可的电子证据固定平台，具有完全法律效力
- **不需要去中心化共识**：这不是加密货币交易，不需要拜占庭容错。繁育者自己签名 + 第三方时间戳 > 50 个矿工确认

### 5.4 联合信任时间戳接入

```javascript
// 申请时间戳（RFC 3161 标准）
// 联合信任 API: https://www.tsa.cn/
async function getTimestamp(hash) {
    // POST hash → TSA → sign → return timestamp token
    const response = await fetch('https://timestamp.tsa.cn/api/v1/timestamp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            hash: hash,
            algorithm: 'sha256'
        })
    });
    return response.json(); // { token: 'MIIG...', timestamp: '2026-05-14T...' }
}
```

---

## 六、龟纹 AI 识别方案

### 6.1 为什么龟壳纹路可行

每只龟的背甲盾片排列是唯一的——这不是"看着像"，而是生物学事实：

- **盾片数量和排列**：椎盾 5 块、肋盾 4+4、缘盾 12+12、颈盾 1、臀盾 2 —— 但实际数量有 ±1 变异
- **生长纹**：每块盾片的同心圆纹路是独一无二的，类似指纹
- **色斑分布**：斑点/放射纹的位置和形状不重复
- **先天损伤**：孵化时的轻微盾片异常终身携带

### 6.2 技术路径

```
阶段 1（MVP，无需训练新模型）：
├── 使用预训练 ResNet50 / EfficientNet-B3 提取特征向量
├── 不需要品种分类（那是品鉴AI的事）
├── 只做 1:1 验证：给两张图 → 提取特征 → 余弦相似度 → 判断是否同一只
└── 阈值：cosine_sim > 0.92 → 同一只（龟壳特征极稳定）

阶段 2（精度提升）：
├── 用滴个龟龟品鉴积累的龟图做对比学习（Siamese Network）
├── 训练目标：最大化同只龟的特征相似度，最小化不同龟的相似度
└── 部署为特征提取服务

阶段 3（自动化出生登记）：
├── 繁育者拍一窝蛋龟苗 → AI 自动检测每只 → 提取特征 → 批量生成锚定
└── 结合 object detection (YOLO) + feature extraction
```

### 6.3 实现伪代码

```python
import torch
import torchvision.transforms as T
from torchvision.models import resnet50
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# 加载预训练模型（去掉分类头）
model = resnet50(pretrained=True)
model.fc = torch.nn.Identity()  # 输出 2048-d 特征向量
model.eval()

transform = T.Compose([
    T.Resize((256, 256)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def extract_bio_features(image_path):
    """从龟壳图片提取生物特征向量"""
    img = Image.open(image_path).convert('RGB')
    # 检测并裁剪龟壳区域（可选：用已有的品鉴AI做ROI）
    img_tensor = transform(img).unsqueeze(0)
    with torch.no_grad():
        features = model(img_tensor).squeeze().numpy()
    return features  # shape: (2048,)

def verify_identity(birth_features, current_features, threshold=0.92):
    """验证当前图片是否与出生锚定为同一只龟"""
    sim = cosine_similarity([birth_features], [current_features])[0][0]
    return {
        'same_individual': sim >= threshold,
        'confidence': float(sim),
        'verdict': 'MATCH' if sim >= threshold else 'MISMATCH'
    }
```

### 6.4 难点与应对

| 难点 | 应对 |
|------|------|
| 龟苗太小，特征不明显 | 出生登记要求高清微距 + 多角度（背甲/腹甲/头纹） |
| 成长后壳纹变化 | 特征提取关注盾片拓扑（不变），非色斑（可变） |
| 不同品种特征差异大 | 按科（龟/蛇/蜥蜴）分别训练特征提取器 |
| 同一窝苗子长得像 | 出生时即独立登记，遗传相似性反而增加验证可信度 |
| 光照/角度影响 | 数据增强 + 多角度注册 + 取最高匹配分 |

---

## 七、API 设计

### 7.1 繁育者认证

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v2/breeders/apply` | 提交认证申请（实名+场地） |
| `GET` | `/api/v2/breeders/:id` | 繁育者信息 + 信誉分 |
| `GET` | `/api/v2/breeders/:id/anchors` | 该繁育者的所有出生登记 |
| `PUT` | `/api/v2/breeders/:id` | 更新场地/品种信息 |
| `GET` | `/api/v2/breeders/leaderboard` | 繁育者信誉排行 |

### 7.2 出生锚定

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v2/anchors` | **出生登记**（照片+GPS+时间→生成锚定） |
| `GET` | `/api/v2/anchors/:anchor_id` | 锚定详情（含完整血统链） |
| `GET` | `/api/v2/anchors/:anchor_id/chain` | 溯源时间线（出生→所有转移→所有事件） |
| `GET` | `/api/v2/anchors/:anchor_id/verify` | 公开验证信息（hash+时间戳，无需登录） |
| `POST` | `/api/v2/anchors/clutch` | 批量登记一窝苗子 |

### 7.3 身世验证

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v2/verify/photo` | **照片验身**：上传龟照 → AI 匹配 → 返回锚定 ID + 匹配分 |
| `POST` | `/api/v2/verify/transfer` | **转移验证**：交接时双方确认 |
| `GET` | `/api/v2/verify/report/:anchor_id` | 生成验证报告 PDF（法律用途） |

### 7.4 执法专用

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v2/enforce/lookup` | 按照片批量查询（执法用，需授权） |
| `POST` | `/api/v2/enforce/certify` | 出具司法鉴定意见书 |
| `GET` | `/api/v2/enforce/ledger` | 公开账本（所有锚定哈希列表，审计用） |

### 7.5 示例：出生登记流程

```javascript
// POST /api/v2/anchors
// 繁育者端（小程序）
const result = await wx.request({
    url: 'https://api.digeguigui.com/api/v2/anchors',
    method: 'POST',
    header: { 'Authorization': 'Bearer ' + token },
    data: {
        species_id: 82,                    // 黄缘闭壳龟
        individual_name: '2026-CB-001',
        clutch_id: 'HY-2026-05',
        birth_date: '2026-05-10T08:30:00+08:00',
        birth_gps: { lat: 23.1291, lng: 113.2644 },  // 广州
        parent_male_anchor: 'DGG-T-000045',           // 父本锚定号
        parent_female_anchor: 'DGG-T-000046',         // 母本锚定号
        photos: ['cos://...'],             // 出生照片（至少3张：背甲/腹甲/头）
        sex: 'unknown'                     // 幼体通常未知
    }
});

// 返回
{
    "ok": true,
    "data": {
        "anchor_id": "DGG-T-000128",       // 终身锚定号
        "prov_hash": "a1b2c3...",          // 链上哈希
        "timestamp_signature": "MIIG...",  // 时间戳签名
        "biometric_hash": "d4e5f6...",     // 生物特征哈希
        "verification_url": "https://api.digeguigui.com/api/v2/anchors/DGG-T-000128/verify"
    }
}
```

---

## 八、小程序端设计

### 8.1 繁育者面板（新增页面）

```
┌────────────────────────────────┐
│  🧬 我的繁育者面板              │
│                                │
│  ┌──────────────────────────┐  │
│  │ 🏅 认证繁育者              │  │
│  │ 信誉分 98  | 登记 47 窝   │  │
│  └──────────────────────────┘  │
│                                │
│  [➕ 出生登记]  [📋 窝次管理]   │
│                                │
│  最近登记：                     │
│  ┌──────────────────────────┐  │
│  │ DGG-T-000128             │  │
│  │ 黄缘闭壳龟 | 2026-05-10  │  │
│  │ 状态: 🟢 未转移          │  │
│  └──────────────────────────┘  │
│                                │
│  [查看全部锚定记录 →]          │
└────────────────────────────────┘
```

### 8.2 出生登记页

```
┌────────────────────────────────┐
│  📸 出生登记                    │
│                                │
│  品种： [黄缘闭壳龟 ▾]          │
│  窝次号：[HY-2026-05         ] │
│  出生时间：[2026-05-10 08:30 ] │
│                                │
│  📍 出生地点                    │
│  ┌──────────────────────────┐  │
│  │    [地图选点]              │  │
│  │   广东省广州市越秀区       │  │
│  │   23.1291, 113.2644      │  │
│  └──────────────────────────┘  │
│                                │
│  📷 出生照片（至少3张）          │
│  ┌────┐ ┌────┐ ┌────┐         │
│  │背甲│ │腹甲│ │头纹│         │
│  └────┘ └────┘ └────┘         │
│                                │
│  🧬 双亲血统 (可选)             │
│  父本：[DGG-T-000045 ▾]       │
│  母本：[DGG-T-000046 ▾]       │
│                                │
│  [🔒 提交并锚定]               │
└────────────────────────────────┘
```

### 8.3 买家验证页

```
┌────────────────────────────────┐
│  🔍 身世验证                    │
│                                │
│  ┌──────────────────────────┐  │
│  │                          │  │
│  │     [📷 拍摄龟壳]         │  │
│  │     或选择相册            │  │
│  │                          │  │
│  └──────────────────────────┘  │
│                                │
│  ┌──── 匹配结果 ────────────┐  │
│  │ ✅ 匹配成功               │  │
│  │                          │  │
│  │ 锚定号：DGG-T-000128     │  │
│  │ 品种：黄缘闭壳龟          │  │
│  │ 匹配度：96.3%            │  │
│  │                          │  │
│  │ 🟢 CB（人工繁育）         │  │
│  │    锚定时间：2026-05-10  │  │
│  │    出生地点：广州越秀    │  │
│  │    登记繁育者：★★★陈师傅 │  │
│  │    成长记录：3 次         │  │
│  │                          │  │
│  │ [查看完整溯源链 →]       │  │
│  │ [下载验证报告 →]         │  │
│  └──────────────────────────┘  │
└────────────────────────────────┘
```

### 8.4 溯源时间线（核心展示）

```
┌────────────────────────────────┐
│  🕐 溯源时间线                  │
│  DGG-T-000128 · 黄缘闭壳龟     │
│                                │
│  ● 2026-05-10                  │
│  │ 🐣 出生登记 — 繁育者·陈师傅  │
│  │ 地点：广州越秀               │
│  │ 父本：DGG-T-000045          │
│  │ 母本：DGG-T-000046          │
│  │ 锚定哈希：a1b2c3... ✓       │
│  │                             │
│  ● 2026-06-15   👤 陈师傅      │
│  │ 📝 喂食习惯                  │
│  │    爱吃小鱼虾，不碰龟粮      │
│  │                             │
│  ● 2026-07-20   👤 陈师傅      │
│  │ 📏 首次体检                  │
│  │    体重：28g · 体长：4.2cm  │
│  │    特征匹配：98.7%           │
│  │                             │
│  ● 2026-09-01                  │
│  │ 🤝 所有权转移               │
│  │    陈师傅 → 张先生          │
│  │    成交价：¥2,800           │
│  │    交接验证匹配：96.3%       │
│  │                             │
│  ● 2026-09-10   👤 张先生      │
│  │ 🏠 环境适应                  │
│  │    换了深水缸，前两天躲角落  │
│  │    第三天开始游了            │
│  │                             │
│  ● 2026-10-01   👤 张先生      │
│  │ 🍽 喂食偏好                  │
│  │    开始接受龟粮了            │
│  │    推荐高够力三色            │
│  │                             │
│  ● 2026-12-25   👤 张先生      │
│  │ 📏 冬眠前测量                │
│  │    体重：45g · 体长：5.1cm  │
│  │    特征匹配：95.8%           │
│  │                             │
│  [验证完整性 ✓]                │
└────────────────────────────────┘
```

---

## 九、盈利模型升级

加入 Provenance 后，整个商业模型从"卖信息"升级为"卖信任"：

| 层级 | 产品 | 定价 | 频次 |
|------|------|------|------|
| 🔓 免费 | 买家扫码验证 | ¥0 | 无限 |
| 🔓 免费 | 基础繁育者登记 | ¥0 | 一次 |
| 💰 基础 | **AI品鉴** | ¥9.9/次 | 按次 |
| 💰 基础 | **出生锚定** | ¥19.9/窝 | 按窝 |
| 💰 进阶 | **繁育者认证** | ¥99/年 | 年付 |
| 💰 进阶 | **Provenance 完整版** | ¥199/年 | 年付 |
| 💎 企业 | **B2B API** | ¥5K-50K/年 | 年付 |
| 💎 政府 | **执法鉴定 API** | 合同 | 年付 |
| 💎 保险 | **异宠保险数据** | 分成 | 持续 |

---

## 十、法律护城河

### 10.1 时间戳法律效力

- 联合信任时间戳（tsa.cn）：最高人民法院《关于互联网法院审理案件若干问题的规定》第11条明确认可
- RFC 3161 时间戳 + 数字签名 = 完整的电子证据链
- 出生锚定记录 = 可以当呈堂证供

### 10.2 执法合作切入点

```
CITES 执法痛点：
├── 查获活体龟 → 无法判定 CB/WC → 正常查扣还是刑事立案？
├── 滴个龟龟介入：
│   ├── 拍照 → AI 搜索锚定数据库
│   ├── 匹配到出生记录 → 确认 CB → 免于刑事追究
│   └── 无任何记录 → 标记为 "来源不明" → 进一步调查
└── 提出合作：林业局/CITES管理机构 → 免费提供执法查询接口
```

### 10.3 可申请的知产保护

| 类型 | 内容 | 策略 |
|------|------|------|
| **软著** | Provenance 系统源代码 | 代码完成即登记 |
| **发明专利** | "基于生物特征识别的爬宠个体身份锚定方法" | 方法专利，保护算法 |
| **实用新型** | 龟壳纹路特征提取装置（如果有硬件） | 如果出硬件 |
| **商标** | "滴个龟龟 Provenance" 认证标识 | 视觉标识，不可伪造 |

---

## 十一、分阶段实施计划

### Phase 1：MVP（2 周）

```
目标：跑通"出生登记 → 特征提取 → 验证"最小闭环

交付物：
├── 数据库 migration（4 张新表）
├── AI 特征提取服务（ResNet50 预训练）
├── 出生登记 API（POST /api/v2/anchors）
├── 拍照验证 API（POST /api/v2/verify/photo）
├── 哈希链生成逻辑（自建链）
├── 小程序出生登记页
└── 小程序 "我的一窝" 页面

里程碑：用 1 窝真实的黄缘闭壳龟苗跑通全流程
```

### Phase 2：信任链（2 周）

```
目标：加上时间戳 + 公开锚定 + 转移记录

交付物：
├── 联合信任时间戳集成
├── 公开锚定页（transparency.digeguigui.com）
├── 所有权转移 API + 页面
├── 溯源时间线页面
├── 繁育者认证体系
└── 数字签名（ed25519 密钥对生成）

里程碑：完成 3 次转移后，溯源链完整可验证
```

### Phase 3：壁垒（2 周）

```
目标：执法接口 + 增长飞轮

交付物：
├── 执法查询 API
├── 验证报告 PDF 生成
├── 繁育者信誉排行
├── 市场集成（转移记录 → 价格数据沉淀）
├── Merkle Root 定期发布（公众号/Gitee）
└── 特征模型微调（Siamese Network）

里程碑：与至少 5 位繁育者建立合作
```

---

## 十二、与现有系统集成

```
已有模块 → Provenance 关联方式

品系基因库 → 双亲血统记录可追溯基因型
价格引擎   → 锚定记录 → 真实成交价 → 反哺价格模型
品鉴AI     → 龟纹 ROI 检测复用品鉴的特征提取层
饲养参数   → 成长事件中的体重/体长 → 生长曲线对比
微信支付   → 出生锚定付费（¥19.9/窝）
认证系统   → 繁育者 KYC 复用现有微信登录
```

---

## 十三、风险与应对

| 风险 | 概率 | 应对 |
|------|------|------|
| 繁育者不愿公开 GPS | 中 | 模糊到区县级即可（广州越秀），不需要精确到门牌号 |
| WC 龟冒充 CB 后补登记 | 高 | 出生登记要求幼体照片 + AI 检测幼体特征（尺寸/卵齿/卵黄囊残留） |
| 买家不验 | 中 | 卖家端驱动：不验 = 无法证明 CB = 卖不上价 |
| 模型把同窝兄弟当成同一只 | 中 | 出生时独立登记 + 多模态（背甲+腹甲+头纹）联合匹配 |
| 法律监管风险 | 低 | 所有数据境内存储，不做加密货币交易，只做存证 |
| 执法部门不认可 | 中 | 联合信任时间戳有最高法背书，电子证据效力已有判例 |

---

## 十四、一句话总结

**滴个龟龟的终局不是"识龟 App"，而是爬宠行业的信任基础设施。**

品系基因库是"知道这是什么"，价格引擎是"知道它值多少钱"，Provenance 系统是"知道它从哪来、干不干净、能不能买"。

三者闭环后，任何后来者要抄——不是抄代码能解决的，繁育者网络 + 生物特征数据库 + 哈希时间戳链的三重壁垒，是时间换来的，不是代码换来的。

---

*技术方案 v1.0 · 等待用户确认后进入 Phase 1 开发*
