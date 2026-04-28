# web-access — 联网 + CDP 浏览器自动化

**中文** | [English](./README_EN.md)

`presales-skills` marketplace 的**共享 plugin**，给 AI Agent 装上完整联网能力——WebSearch / WebFetch / curl / Jina / CDP 浏览器自动化的统一调度，以及登录态站点抓取与站点经验积累。被 solution-master / tender-workflow 共同依赖（cdp_sites 启用或 MCP 搜索注册时）。

> 🙏 **致谢上游**：本 plugin 整包 vendored 自 [eze-is/web-access](https://github.com/eze-is/web-access) v2.5.0（MIT License © 一泽 Eze）——核心 SKILL.md、CDP Proxy 脚本、references、设计哲学均沿用上游设计与实现。本仓适配 presales-skills marketplace 体例（路径替换 + plugin 集成 + 新增 `mcp_installer.py` 工具）。感谢一泽 Eze 的开源工作。详细借用清单与原项目 LICENSE 见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。

---

## 核心能力

- **联网工具自动选择**：WebSearch / WebFetch / curl / Jina / CDP，按场景自主判断，可任意组合
- **CDP Proxy 浏览器操作**：直连用户日常 Chrome，天然携带登录态，支持动态页面、交互操作、视频截帧
- **三种点击方式**：`/click`（JS click）、`/clickAt`（CDP 真实鼠标事件）、`/setFiles`（文件上传）
- **本地 Chrome 书签 / 历史检索**：`find-url.mjs` 查询公网搜不到的目标（内部系统）或用户访问过的页面
- **并行分治**：多目标时分发子 Agent 并行执行，共享一个 Proxy，tab 级隔离
- **站点经验积累**：按域名存储操作经验（URL 模式、平台特征、已知陷阱），跨 session 复用
- **媒体提取**：从 DOM 直取图片 / 视频 URL，或对视频任意时间点截帧分析
- **MCP 搜索注册器**（presales-skills 集成）：内置 `mcp_installer.py`，被 `/twc setup` / `/solution-master setup` 调用一键注册 tavily / exa / minimax-token-plan 三类 web 搜索 MCP 到 `~/.claude.json`

## Slash 入口

| 触发方式 | 形式 |
|---|---|
| Claude Code canonical | `/web-access:browse "..."` |
| Codex / Cursor / OpenCode 短形式 alias | `/browse "..."` |
| 自然语言 auto-trigger | "帮我搜一下 X" / "抓一下这个页面" / "去小红书搜 xxx" / "帮我在创作者平台发图文" / "同时调研这 5 个产品官网" |

## 详细使用文档

完整能力清单、CDP Proxy API 详解、MCP 注册工具用法、设计哲学等见 sub-skill README:

→ [`skills/browse/README.md`](./skills/browse/README.md) | [`skills/browse/README_EN.md`](./skills/browse/README_EN.md)

## 安装

> **安装**：见仓库根 [README.md#安装](../README.md#安装)（作为 `presales-skills` umbrella marketplace 的 shared plugin 一并装）。

CDP 模式额外需要 **Node.js 22+** 和 Chrome 远程调试。详见 [`skills/browse/README.md` §前置配置（CDP 模式）](./skills/browse/README.md#前置配置cdp-模式)。

> 上游独立分发：[eze-is/web-access](https://github.com/eze-is/web-access)（不通过 presales-skills 时的独立装载路径）。

## 与其它 plugin 的关系

| 主 plugin | 用 web-access 做什么 |
|---|---|
| **solution-master** | CDP 登录态站点检索（`cdp_sites.enabled=true` 时必需）；`mcp_installer.py` 注册 MCP 搜索工具 |
| **tender-workflow** | `/twc setup` 调用 `mcp_installer.py` 注册 tavily / exa / minimax；taw 撰章节时 MCP 搜索 |

未装 web-access 时主 plugin 自动降级到内置 `WebSearch`。

## ⚠️ 使用前提醒

通过浏览器自动化操作社交平台（如小红书）存在账号被平台限流或封禁的风险。**强烈建议使用小号进行操作。**

## 第三方组件

整包 vendored 自 [eze-is/web-access](https://github.com/eze-is/web-access) v2.5.0（MIT License）。详见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。
