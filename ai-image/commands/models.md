---
description: 展示 AI 图片生成的统一模型注册表（13 provider）。Markdown 表格格式。可选 provider 名过滤，--refresh 尝试联网更新（当前版本未实现）。
---

调用 ai-image plugin 的统一配置 CLI 的 `models` 子命令：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ai_image_config.py models $ARGUMENTS
```

$ARGUMENTS 为可选 provider 名（ark/dashscope/gemini/openai/...）或 --refresh 标记。
