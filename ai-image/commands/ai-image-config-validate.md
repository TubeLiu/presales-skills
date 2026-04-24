---
description: 健康检查：逐 provider 确认 API key 已在 config.yaml 或环境变量中配置。可选 provider 名过滤。
---

调用 ai-image plugin 的统一配置 CLI 的 `validate` 子命令：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ai_image_config.py validate $ARGUMENTS
```

$ARGUMENTS 为可选单个 provider 名。当前版本只检查 key 是否配置，不发真实 API 调用。
