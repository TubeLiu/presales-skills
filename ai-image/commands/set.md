---
description: 按 dotted path 设置配置项。例如：/ai-image:set api_keys.ark sk-xxx
---

调用 ai-image plugin 的统一配置 CLI 的 `set` 子命令：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ai_image_config.py set $ARGUMENTS
```

用户传入形如 `api_keys.ark sk-xxxx` 的参数。脚本自动识别 true/false/null/int/float 类型。
