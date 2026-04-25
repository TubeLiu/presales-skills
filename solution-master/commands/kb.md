---
description: 知识检索——从本地 KB / AnythingLLM 语义搜索 / 互联网多源 / CDP 登录态站点检索素材，并智能融合，用于方案撰写或头脑风暴。
---

用户运行了 `/solution-master:kb $ARGUMENTS` —— 请激活 solution-master plugin 的 `knowledge-retrieval` skill 处理：

`$ARGUMENTS`

详细工作流见 `skills/knowledge-retrieval/SKILL.md`。

## 数据源

- 本地 KB（`~/.config/solution-master/localkb/` 索引）
- AnythingLLM 语义搜索（如已安装 anythingllm-mcp plugin）
- 互联网检索（Tavily / Exa / WebSearch）
- CDP 登录态站点（如 `cdp_sites.enabled=true`，需 web-access plugin）
