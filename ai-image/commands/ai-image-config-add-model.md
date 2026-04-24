---
description: 追加用户自定义模型到 ~/.config/presales-skills/models-user.yaml。不污染 plugin 分发的注册表。
---

调用 ai-image plugin 的统一配置 CLI 的 `add-model` 子命令：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ai_image_config.py add-model $ARGUMENTS
```

$ARGUMENTS 需包含两个参数：`<provider> <yaml-fragment>`。yaml-fragment 必须含 `id` 字段。
示例：
```
/ai-image-config-add-model ark '{"id": "custom-model", "name": "Custom", "status": "available"}'
```
