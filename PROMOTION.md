# 滴个龟龟 MCP — 推广提交清单
# 按优先级排序，每个渠道 30 秒搞定

## 🔥 渠道 1: GitHub awesome-mcp-servers (5551⭐) — 最高优先级

**操作**：打开 https://github.com/appcypher/awesome-mcp-servers/edit/main/README.md
**位置**：找到 `## 🧬 <a name="research-data"></a>Research & Data` 段
**插入**：在最后一个 `- <img` 行之后、`<br />` 之前，加一行：

```
- <img src="https://api.digeguigui.com/favicon.ico" height="14"/> [滴个龟龟 — Digeguigui](https://github.com/zhanghao0971/digeguigui) - Global reptile & exotic pet knowledge base. 633 species, AI species identification, genetics calculator (Punnett), 12-dimension care parameters, health symptom diagnosis, pricing estimation, and blockchain-anchored provenance verification. Free tier with 9 tools, 10 req/min. MCP endpoint: https://api.digeguigui.com/mcp
```

**PR 标题**：`Add Digeguigui - Reptile knowledge base MCP server`
**PR 描述**：
```
## 滴个龟龟 (Digeguigui) — Global Reptile Knowledge MCP Server

- 633 species (368 turtles, 91 snakes, 77 lizards, 60 frogs, 36 geckos)
- 9 free tools: species search, AI photo identification, genetics calculator, health diagnosis, price estimation, care parameter lookup
- 183 genes, 192 combo morphs, 56 species with market prices
- Free tier: instant API key via POST /api/mcp-keys/apply
- MCP endpoint: https://api.digeguigui.com/mcp
- Discovery: https://api.digeguigui.com/.well-known/mcp
```

---

## 🔥 渠道 2: mcp.so 目录

**操作**：打开 https://github.com/chatmcp/mcpso/issues/new
**标题**：`Server Submission: 滴个龟龟 — Digeguigui (Reptile Knowledge Base)`
**内容**：
```
**Server Name**: 滴个龟龟 (Digeguigui)
**Description**: Global reptile & exotic pet knowledge base. 633 species, AI identification, genetics calculator, health diagnosis, pricing, provenance verification.
**MCP Endpoint**: https://api.digeguigui.com/mcp
**Transport**: HTTP (Streamable)
**Authentication**: x-api-key header (free key via POST /api/mcp-keys/apply)
**Tools (10 total)**: search_species, get_species_profile, identify_turtle, estimate_value, genetics_calculator, search_by_traits, health_check, db_stats, verify_provenance (Pro)
**GitHub**: https://github.com/zhanghao0971/digeguigui
**Website**: https://digeguigui.com
**Pricing**: Free tier (9 tools, 10 req/min) / Pro (10 tools, 60 req/min)
```

---

## 渠道 3: Smithery.ai

**操作**：如果你有 Smithery 账号，运行：
```bash
npx @smithery/cli mcp add https://api.digeguigui.com/mcp --id digeguigui
```
或通过网页 https://smithery.ai 提交。

---

## 渠道 4: 小红书 / 即刻 / V2EX

简单发帖：
> 🐢 给 AI Agent 用的爬宠知识库上线了 — 滴个龟龟 MCP Server
> 633种龟蛇蜥蜴蛙，识图·基因计算·健康诊断·估价，9个免费工具
> Agent 一键自取 Key：POST api.digeguigui.com/api/mcp-keys/apply
> 欢迎 Cursor/Claude/Copilot 用户来玩 👇
> https://digeguigui.com
