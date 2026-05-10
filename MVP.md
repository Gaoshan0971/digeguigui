# 滴个龟龟 MVP 方案

> 目标：用最少的代码验证「品系图谱 + 展示墙」的核心价值。
> 预估周期：2-4周（1人全栈）

---

## MVP 范围（第一期只做一个品种）

**选择品种：蛋龟 🥚🐢**
理由：
1. 你最熟，种子用户容易拉
2. 蛋龟品系体系不如球蟒复杂，图谱更容易搭建
3. 国内蛋龟圈活跃、交易频繁、品相标准正在形成
4. 价格波动大，价格气象站需求真实

---

## MVP 功能清单（精简到极致）

### Phase 1.0 — "看得懂"（第1-2周）

| 功能 | 复杂程度 | 说明 |
|------|----------|------|
| 蛋龟品系图谱 | ⭐⭐⭐ | 手动录入主要品系（白化、果核、巨头、麝香等），配文字描述+参考图 |
| 图片上传+展示墙 | ⭐⭐ | 用户上传蛋龟照片+文字标签，瀑布流展示 |
| 简单的同城爬友 | ⭐ | 用户选择所在城市，看到同城爬友展示 |
| 点赞互动 | ⭐ | 给喜欢的藏品点赞 |
| 微信登录 | ⭐⭐ | 复用搭肩空投的微信授权登录流程 |

**不做**（此阶段）：
- AI品系鉴定（AI留到Phase 2）
- 基因组合计算器（不涉及球蟒，蛋龟基因没有那么多组合）
- 价格气象站（需要社区活跃后才能收集数据）
- 繁育者认证/付费（先验证核心需求）

### Phase 1.1 — "想晒想认"（第3-4周）

| 功能 | 复杂程度 | 说明 |
|------|----------|------|
| AI品系识别（蛋龟版） | ⭐⭐⭐⭐ | 拍照→AI识别品系→自动打标签关联到图谱 |
| 繁育记录 | ⭐⭐⭐ | 上传配对信息、标记后代品相 |
| 价格随手填 | ⭐ | 用户自愿标注"入手价"，聚合价格区间展示 |
| 分享卡片生成 | ⭐⭐ | 藏品图→生成鉴赏卡片→朋友圈/微信群分享 |

---

## 数据库设计

### 核心表

```sql
-- 品系图谱主表
CREATE TABLE morphs (
  morph_id INTEGER PRIMARY KEY AUTOINCREMENT,
  species TEXT NOT NULL,               -- 品种：egg_turtle, ball_python, leopard_gecko...
  name TEXT NOT NULL,                   -- 品系名称
  parent_morph_id INTEGER,              -- 父品系（用于构建品系树）
  genetic_formula TEXT DEFAULT '',      -- 基因型组合描述
  description TEXT DEFAULT '',          -- 品系描述
  visual_ref_url TEXT DEFAULT '',       -- 参考图
  rarity INTEGER DEFAULT 0,            -- 稀有度 1-10
  sort_order INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 繁育记录
CREATE TABLE breedings (
  breeding_id INTEGER PRIMARY KEY AUTOINCREMENT,
  breeder_id INTEGER NOT NULL,          -- 繁育者用户ID
  sire_morph_id INTEGER,                -- 父本品系
  dam_morph_id INTEGER,                 -- 母本品系
  pairing_date TEXT,
  notes TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 收藏品展示
CREATE TABLE collections (
  collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  morph_id INTEGER,                     -- 关联品系
  image_urls TEXT DEFAULT '[]',          -- 图片
  caption TEXT DEFAULT '',              -- 描述
  price REAL DEFAULT 0,                 -- 入手价（可选）
  city TEXT DEFAULT '',                 -- 所在城市
  likes INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 点赞
CREATE TABLE likes (
  like_id INTEGER PRIMARY KEY AUTOINCREMENT,
  collection_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  created_at TEXT DEFAULT (datetime('now','localtime')),
  UNIQUE(collection_id, user_id)
);
```

---

## 页面结构

```
miniprogram/pages/
├── index/             # 首页 - 推荐展示墙（瀑布流）
├── morph-tree/        # 品系图谱（蛋龟品系树）
├── morph-detail/      # 单个品系详情
├── upload/            # 上传藏品
├── collection/        # 藏品详情页
├── my/                # 个人中心 - 我的藏品、我的繁育记录
└── city/              # 同城爬友
```

**TabBar**：首页 | 品系图谱 | 上传 | 同城 | 我的

---

## API 接口（MVP最小集）

### 无需登录
- `GET /api/morphs?species=egg_turtle` — 获取品系图谱树
- `GET /api/morphs/:id` — 品系详情
- `GET /api/collections?morph_id=&city=&page=` — 展示墙列表瀑布流
- `GET /api/collections/:id` — 藏品详情

### 需登录
- `POST /api/collections` — 上传藏品
- `POST /api/likes` — 点赞/取消
- `POST /api/breedings` — 添加繁育记录
- `GET /api/breedings?user_id=` — 我的繁育记录
- `GET /api/mine/collections` — 我的藏品

---

## 项目初始化步骤

```bash
# 1. 在 Gitee 创建私有仓库 digeguigui
# 2. 本地初始化
cd /d/Zhanghao/Digeguigui
git init
git remote add origin https://gitee.com/zhanghao0971/digeguigui.git

# 3. 创建目录结构
mkdir -p miniprogram/pages/{index,morph-tree,morph-detail,upload,collection,my,city}
mkdir -p miniprogram/images
mkdir -p server/{routes,services,static}
mkdir -p data          # SQLite数据库目录

# 4. 初始化服务端
cd server
npm init -y
npm install better-sqlite3 cos-nodejs-sdk-v5 multiparty
```

---

## MVP 里程碑

| 周 | 交付物 | 验证标准 |
|----|--------|----------|
| 第1周 | 蛋龟品系图谱数据录入 + 展示墙基础 | 打开能看到品系树和种子藏品 |
| 第2周 | 上传藏品 + 点赞 + 同城展示 | 种子用户能把真实藏品传上去，能看到同城爬友 |
| 第3周 | AI品系识别（简单版） | 拍张蛋龟照片能标出品系名称 |
| 第4周 | 繁育记录 + 分享卡片 + 内测上线 | 5-10位爬友持续使用 |

---

## 技术栈清单

| 层 | 技术 | 备注 |
|----|------|------|
| 小程序 | 微信原生框架 | 与搭肩空投一致 |
| API | Node.js + http原生模块 | 复用搭肩空投的server架构 |
| 数据库 | better-sqlite3 | 单库单机，省运维 |
| 图片存储 | COS对象存储 | 复用已有腾讯云COS |
| AI识别 | 大模型视觉API | 对接云端API，不做本地模型 |
| 部署 | 阿里云 8.138.171.33 | 复用现有服务器，新增端口 |

---

## 风险与应对

| 风险 | 可能性 | 应对 |
|------|--------|------|
| 种子用户拉不动 | 中 | 先用自己的藏品填充，有了内容再拉人；先做工具价值（繁育记录）再推社区 |
| 品系数据太多人工录入慢 | 高 | 先只录蛋龟TOP10品系，后续开放用户共建 |
| AI识别不准 | 中 | 初期做半自动：AI推荐+用户手动确认，数据和标注逐渐积累 |
| 社区变成死水 | 中 | 同城线下品鉴会是很好的破冰手段，先组织1次线下活动激活 |
