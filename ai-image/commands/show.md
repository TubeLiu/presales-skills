---
description: 展示当前 AI 图片生成配置。API keys 自动 masked。可选 section 参数过滤（api_keys/ai_image/localkb/...）。
---

调用 ai-image plugin 的统一配置 CLI 的 `show` 子命令：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ai_image_config.py show "$ARGUMENTS"
```

$ARGUMENTS 为可选 section 名（如 `api_keys`、`ai_image`）。不传则展示全部。
