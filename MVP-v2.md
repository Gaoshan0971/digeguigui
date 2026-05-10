# 滴个龟龟 MVP 方案 v2

> 修订日期：2026-05-10
> 修订原因：基于圈子真实用户画像重构产品定位和 MVP 优先级

---

## 一、用户画像（真实版）

龟圈用户的真实旅程：

```
入坑 → 收壳（不断死）→ 养活几只 → 开始认品种
                                         │
            ┌────────────────────────────┘
            ▼
      认出好坏 → 买"名龟"收藏 → 看血统/看出身
            │
            ▼
      建立自己的品相标准（各说各的）
```

**核心洞察**：

1. 370+ 龟种，普通玩家认不出 20 种。**品种识别是刚需。**
2. 温湿光风喂不对就死龟。**分品种系统饲养知识是刚需。**
3. 品相决定价格，但没有统一标准。**品相评级体系是蓝海。**
4. 不懂的品种、不确定的品相，扔上来大家鉴定——**鉴赏本身就是社交货币。**
5. 有了血统记录，卖家有动力维护信誉，买家才敢下手——**血统 = 信任基础设施。**

---

## 二、重新定位

> **从"品系图谱社区" → "龟类全周期工具 + 信任平台"**

| 原定位 | 新定位 |
|--------|--------|
| 爬宠收藏品展示社区 | 龟类识别 + 饲养 + 品相 + 血统一站式平台 |
| 对标腕表之家 | 对标 iNaturalist（识别）+ 腕表之家（收藏）+ AKC（血统） |
| 品系图谱是基石 | **血统记录是基石**（图谱是有血统数据之后的结果） |
| 先做社区再做工具 | **先做独立工具（AI 识龟 H5）再导流社区** |

---

## 三、核心飞轮

```
          拍照识龟（工具入口）
               │
               ▼
        品种百科 + 饲养指南（留存）
               │
               ▼
     ┌──── 上传藏品 ────┐
     │                  │
     ▼                  ▼
  品相鉴定           血统记录
  （大家帮看）       （繁育者填）
     │                  │
     ▼                  ▼
  品相标准          卖家信誉
  逐渐形成          逐渐建立
     │                  │
     └────── 交汇 ──────┘
               │
               ▼
          买家敢买（信任闭环）
```

**两个关键飞轮**：

- **信任飞轮**：血统记录 → 卖家有历史可查 → 维护信誉 → 买家信任 → 交易更活跃 → 更多人记录血统
- **鉴赏飞轮**：扔图鉴定 → 大家围观鉴赏 → 获得满足感 → 更多人扔图 → 品相数据积累 → 标准逐渐浮现

---

## 四、MVP 功能清单

### Phase 1.0 — "看得懂、养得活"（第 1-2 周）

| 功能 | 优先级 | 说明 |
|------|--------|------|
| AI 拍照识龟 | 🔴 P0 | 370+ 龟种识别，先做 TOP 30 常见品种。**独立 H5 可传播** |
| 品种百科 | 🔴 P0 | 每个品种：图片、特征、习性、品相维度说明 |
| 饲养知识库 | 🔴 P0 | 分品种：温度/湿度/光照/通风/食物/常见病/冬眠参数 |
| 分享卡片 | 🟡 P1 | 识别结果 → 生成品种卡片 → 朋友圈/微信群传播 |

**不做**：上传藏品、品相评级、血统记录、同城爬友

**验证标准**：拍照能识别品种，识别后能看到完整饲养指南。H5 分享卡片能独立传播。

### Phase 1.1 — "晒得出、鉴得了"（第 3-4 周）

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 藏品上传 + 品种挂载 | 🔴 P0 | 上传照片 → AI 识别/手动选品种 → 挂在品种页面下 |
| 品相鉴定（众包） | 🔴 P0 | 每张藏品图自带"求鉴定"，「大家帮看」评论区 |
| 展示墙 | 🟡 P1 | 按品种浏览藏品，默认按品相热度排序 |
| 品相维度标签 | 🔴 P0 | 壳形/头纹/色泽/体型/状态 分维度打分（先人工，数据积累后 AI） |
| 血统记录（基础版） | 🔴 P0 | 繁育者手动记录：父母 ID/品种/品相等级 → 子代 pedigree |
| 繁育者主页 | 🟡 P1 | 繁育者的血统记录一览、信誉分 |

**不做**：价格气象站、AI 全自动鉴定、同城爬友、付费功能

**验证标准**：用户能把龟挂到品种下、其他人能鉴赏评论、繁育者能记录血统。

---

## 五、页面结构（小程序）

```
miniprogram/pages/
├── identify/           # 拍照识龟（首页入口，也是最核心功能）
│   ├── camera          # 拍照界面
│   └── result          # 识别结果 → 品种百科卡片
├── species/            # 品种百科
│   ├── list            # 品种列表（分类浏览）
│   ├── detail          # 品种详情（特征 + 饲养参数 + 该品种藏品）
│   └── care            # 饲养知识（分品种运维手册）
├── collections/        # 藏品
│   ├── upload          # 上传藏品（拍照/选图 → 选品种 → 标签）
│   ├── detail          # 藏品详情（图片 + 品相维度 + 鉴赏评论）
│   └── wall            # 展示墙（按品种浏览）
├── breeding/           # 血统
│   ├── record          # 记录配对/子代
│   ├── pedigree        # 血统树视图
│   └── breeder         # 繁育者主页
├── appraisal/          # 品相鉴定
│   └── detail          # 单只龟的鉴定讨论页
└── my/                 # 个人中心
    ├── collections     # 我的藏品
    ├── breedings       # 我的繁育记录
    └── appraisals      # 我的鉴定历史
```

**TabBar（5 个）**：识龟 | 品种 | 展示 | 血统 | 我的

---

## 六、数据库设计（MVP）

```sql
-- 品种百科
CREATE TABLE species (
  species_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name_cn TEXT NOT NULL,            -- 中文名：黄缘闭壳龟
  name_latin TEXT NOT NULL,         -- 学名
  family TEXT DEFAULT '',           -- 科
  difficulty INTEGER DEFAULT 0,     -- 饲养难度 1-5
  overview TEXT DEFAULT '',         -- 品种概述
  traits JSON DEFAULT '{}',         -- 识别特征 {"壳形":"...", "头纹":"...", ...}
  care_params JSON DEFAULT '{}',    -- 饲养参数 {"temp":"22-28","humidity":"60-80",...}
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 藏品
CREATE TABLE collections (
  collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  species_id INTEGER NOT NULL,       -- 品种
  image_urls TEXT DEFAULT '[]',      -- 图片列表
  caption TEXT DEFAULT '',           -- 描述
  -- 品相维度打分（1-10，0 表示未评分）
  shell_score INTEGER DEFAULT 0,     -- 壳形
  head_score INTEGER DEFAULT 0,      -- 头纹
  color_score INTEGER DEFAULT 0,     -- 色泽
  body_score INTEGER DEFAULT 0,      -- 体型
  health_score INTEGER DEFAULT 0,    -- 状态
  overall_grade TEXT DEFAULT '',     -- 综合品级 S/A+/A/B/C
  price REAL DEFAULT 0,              -- 入手价（选填）
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 鉴赏记录（品相鉴定评论）
CREATE TABLE appraisals (
  appraisal_id INTEGER PRIMARY KEY AUTOINCREMENT,
  collection_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  comment TEXT DEFAULT '',
  -- 鉴赏者对品相的打分
  shell_score INTEGER DEFAULT 0,
  head_score INTEGER DEFAULT 0,
  color_score INTEGER DEFAULT 0,
  body_score INTEGER DEFAULT 0,
  health_score INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 血统记录（繁育配对 → 子代）
CREATE TABLE breedings (
  breeding_id INTEGER PRIMARY KEY AUTOINCREMENT,
  breeder_id INTEGER NOT NULL,        -- 繁育者
  sire_collection_id INTEGER,         -- 父本（关联藏品）
  dam_collection_id INTEGER,          -- 母本（关联藏品）
  pairing_date TEXT,
  offspring_count INTEGER DEFAULT 0,  -- 子代数量
  notes TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 血统子代
CREATE TABLE offspring (
  offspring_id INTEGER PRIMARY KEY AUTOINCREMENT,
  breeding_id INTEGER NOT NULL,
  collection_id INTEGER,             -- 如果子代已被收录为藏品
  description TEXT DEFAULT '',       -- 子代特征描述
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 点赞
CREATE TABLE likes (
  like_id INTEGER PRIMARY KEY AUTOINCREMENT,
  target_type TEXT NOT NULL,          -- 'collection' | 'appraisal'
  target_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  created_at TEXT DEFAULT (datetime('now','localtime')),
  UNIQUE(target_type, target_id, user_id)
);

-- 用户
CREATE TABLE users (
  user_id INTEGER PRIMARY KEY AUTOINCREMENT,
  openid TEXT UNIQUE NOT NULL,       -- 微信 openid
  nickname TEXT DEFAULT '',
  avatar_url TEXT DEFAULT '',
  role TEXT DEFAULT 'hobbyist',      -- 'hobbyist' | 'breeder' | 'expert'
  reputation INTEGER DEFAULT 0,      -- 信誉分
  created_at TEXT DEFAULT (datetime('now','localtime'))
);
```

---

## 七、API 接口（MVP 最小集）

### 无需登录
- `GET /api/species` — 品种列表（分页）
- `GET /api/species/:id` — 品种详情 + 饲养参数
- `GET /api/species/:id/collections?page=&sort=` — 某品种下的藏品
- `GET /api/collections/:id` — 藏品详情 + 鉴赏评论
- `GET /api/collections/:id/appraisals?page=` — 鉴赏评论列表
- `GET /api/breedings/:id/pedigree` — 血统树数据

### 需登录
- `POST /api/collections` — 上传藏品
- `POST /api/appraisals` — 提交鉴赏（品相打分+评论）
- `POST /api/likes` — 点赞/取消
- `POST /api/breedings` — 记录繁育配对
- `POST /api/breedings/:id/offspring` — 添加子代记录
- `GET /api/mine/collections` — 我的藏品
- `GET /api/mine/breedings` — 我的繁育记录
- `GET /api/breeders/:id` — 繁育者主页（藏品列表 + 血统树 + 信誉分）

---

## 八、AI 策略

### 品种识别（Phase 1.0）

```
用户拍照 → 云端大模型视觉 API
  → 返回 TOP 3 候选品种 + 置信度
  → 用户确认/选择正确品种
  → 数据积累 → 微调专用模型
```

初期做个简单的品种识别就行，不求精确到品相层面。核心价值是"370 种龟我分不清，AI 帮我分"。

### 品相初评（Phase 1.1 后期）

```
藏品上传 → AI 预判品相维度分数（参考值）
  → 展示时标注"AI 参考评级：A"
  → 鉴赏者可以同意/覆盖 AI 评级
  → 多人评级取加权平均 → 品相标准逐渐浮现
```

---

## 九、传播钩子

### 独立 H5：拍照识龟

```
花鸟市场看到一只龟
  → 打开微信扫一扫 / 拍照
  → 滴个龟龟 H5 识别：「这是黄缘闭壳龟，国龟之王 🐢✨」
  → 卡片展示：品种特征 + 饲养难度 + 参考价格区间
  → 「查看更多龟种识别」→ 跳小程序
  → 「分享给龟友」→ 生成朋友圈卡片
```

**这个 H5 不需要任何用户内容就能独立传播**，是真正的冷启动引擎。

---

## 十、技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 小程序 | 微信原生框架 | 复用搭肩空投经验 |
| H5 识龟 | 独立 HTML 页面 | 纯前端 + 云函数调 AI |
| API | Node.js + better-sqlite3 | 单库单机，零运维 |
| 数据库 | SQLite (WAL 模式) | 轻量，够用 |
| 图片存储 | 腾讯云 COS | 复用搭肩空投 |
| AI 识别 | 云端视觉大模型 API | 先调 API，不本地部署 |

---

## 十一、里程碑

| 周 | 交付物 | 验收标准 |
|----|--------|----------|
| 第 1 周 | AI 拍照识龟 H5 + 品种百科 TOP 30 | 拍照能识别出正确品种，含基础特征和饲养参数 |
| 第 2 周 | 小程序框架 + 藏品上传 + 品种挂载 | 能上传龟照、选品种、看到自己的藏品在品种页下 |
| 第 3 周 | 品相鉴定（众包鉴赏）+ 展示墙 | 扔图上来看品相，大家围观打分评论 |
| 第 4 周 | 血统记录 + 繁育者主页 + 内测上线 | 5-10 个种子繁育者的血统记录上链，公开可见 |

---

## 十二、与原 MVP 方案的关键差异

| 维度 | v1（原方案） | v2（修订案） |
|------|-------------|-------------|
| 产品定位 | 品系图谱展示社区 | **识别 → 饲养 → 品相 → 血统** 全周期工具 |
| MVP 品种 | 蛋龟 | **全部龟种**（先做 TOP 30 常见种） |
| 核心入口 | 展示墙 | **AI 拍照识龟 H5**（独立传播） |
| 差异化 | 品系基因树 | **血统记录 → 卖家信誉 → 买家信任** |
| 社交机制 | 点赞 + 同城 | **扔图众包鉴定**（鉴赏本身就是满足） |
| 冷启动 | 自己填充内容 | **H5 病毒传播**，不依赖种子内容 |
| 先发功能 | 图谱 + 展示墙 + 同城 | **识龟 + 饲养 + 鉴定** |
| 推迟功能 | AI 鉴定放 Phase 2 | AI 鉴定从 Day 1 就上线（半自动） |
| 砍掉 | — | 同城爬友（等有密度再说） |
