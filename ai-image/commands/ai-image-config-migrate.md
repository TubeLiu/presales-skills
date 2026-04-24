---
description: 合并旧的 ~/.config/solution-master/config.yaml 和 ~/.config/tender-workflow/config.yaml 到统一位置 ~/.config/presales-skills/config.yaml。幂等（hash 匹配则跳过）。
---

调用 ai-image plugin 的统一配置 CLI 的 `migrate` 子命令：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ai_image_config.py migrate
```

字段映射规则详见 ai_image_config.py FIELD_MAPPING。api_keys 冲突时 tender-workflow 优先，冲突值保留在 api_keys_conflicts section 供人工复核。
