# 🐢 滴个龟龟 MCP Server

全球最大爬宠知识库 — 为 AI Agent 打造的 **633 种爬宠异宠** 识别·饲养·品系·基因·价格·健康·身份验证一体化工具。

```
🔍 识龟  📋 品种档案  🧬 基因计算  💰 估价  
🔍 饲养反查  🩺 健康诊断  📊 数据统计  🎫 身份验证
```

## 快速开始

**Agent 自取 Key（零人类介入）**：
```bash
curl -X POST https://api.digeguigui.com/api/mcp-keys/apply \
  -H "Content-Type: application/json" \
  -d '{"name":"my-agent"}'
# → {"api_key":"dg-fre-xxx", "tier":"free", "rate_limit":"10次/分钟"}
```

**配置 MCP 客户端**：
```json
{
  "mcpServers": {
    "digeguigui": {
      "url": "https://api.digeguigui.com/mcp",
      "headers": { "x-api-key": "dg-fre-YOUR_KEY" }
    }
  }
}
```

## 10 个工具

| 工具 | 描述 | Tier |
|------|------|------|
| `search_species` | 搜索品种 — 中文/拉丁/俗称/分组 | Free |
| `get_species_profile` | 品种完整档案 — 分类/12维饲养参数/价格/别名 | Free |
| `identify_turtle` | 拍照识龟 — AI识别品种+置信度 | Free |
| `estimate_value` | 价值预估 — 基础价+品系基因溢价×品级系数 | Free |
| `genetics_calculator` | Punnett基因计算器 — 显/隐/共显/多基因 | Free |
| `search_by_traits` | 按饲养条件反查 — "新手+小型+水栖+25°C" | Free |
| `health_check` | 症状诊断 — 龟/蛇/蜥蜴/蛙常见病 | Free |
| `db_stats` | 数据库全景 — 物种/品系/基因/价格覆盖 | Free |
| `verify_provenance` | 扫码验证爬宠身份证 — Git存证哈希 | Pro |
| `compare_species` | 品种对比（即将上线） | — |

## 定价

| Tier | 限速 | 工具 | 获取方式 |
|------|------|------|----------|
| **Free** | 10次/分钟 | 9个 | `POST /api/mcp-keys/apply` 即时获取 |
| **Pro** | 60次/分钟 | 10个（含身份验证） | 联系升级 |
| **Enterprise** | 定制 | 全部 + 数据导出 | 联系我们 |

## 数据规模

- 🐢 龟类 368 | 🐍 蛇 91 | 🦎 蜥蜴 77 | 🐸 蛙 60 | 守宫 36
- 🧬 183 基因 · 192 组合品系
- 💰 56 品种国内价格 · 国际站数据
- 🩺 14 种常见病诊断知识库

## 发现

- MCP 端点: `https://api.digeguigui.com/mcp`
- 服务发现: `https://api.digeguigui.com/.well-known/mcp`
- OpenAPI: `https://api.digeguigui.com/openapi.json`
- 官网: `https://digeguigui.com`

## 技术栈

Python HTTP Server · SQLite · MCP JSON-RPC 2.0 · REST API
