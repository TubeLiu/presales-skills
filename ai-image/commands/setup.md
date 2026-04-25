---
description: AI 图片生成首次交互式配置向导。写入 ~/.config/presales-skills/config.yaml 的骨架并提示用户下一步。
---

AI 生图相关配置（API keys / 默认 provider / 模型）由 ai-image plugin 持有；本命令是配置入口。

调用 ai-image plugin 的统一配置 CLI 的 `setup` 子命令：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ai_image_config.py setup
```

向导会创建默认配置骨架。用户填 API keys 的最常用 3 条命令：
```
/ai-image:set api_keys.ark <key>
/ai-image:set api_keys.dashscope <key>
/ai-image:set api_keys.gemini <key>
```

如使用 solution-master / tender-workflow，请另行运行 `/solution-config setup` / `/twc setup` 配置各自的专属项（localkb / anythingllm / cdp_sites / taa-taw-tpl-trv 等）。
