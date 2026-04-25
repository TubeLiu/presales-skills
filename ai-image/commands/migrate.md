---
description: 把 ~/.config/{solution-master,tender-workflow}/config.yaml 中的 api_keys / ai_image / ai_keys 三个块抽到 ~/.config/presales-skills/config.yaml；其余 plugin 专属字段（cdp_sites/taa-taw/localkb 等）保留在源文件不动。
---

调用 ai-image plugin 的统一配置 CLI 的 `migrate` 子命令：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ai_image_config.py migrate
```

## 行为

- **范围**：仅迁移 `api_keys`、`ai_image` 两个顶层块；同时识别超老 schema `ai_keys.{ark,dashscope,gemini}_api_key` 并 lift 到 `api_keys.*`。
- **幂等**：每次运行都重算合并；如源文件已无这三个块直接退出。`api_keys_conflicts` 字段每轮重新构造（pop 后重写），用户手工编辑该字段会被覆盖。
- **优先级（api_keys 冲突）**：`presales-skills` 现有值 > `tender-workflow` > `solution-master`。差异值写入 `api_keys_conflicts` 供人工复核。
- **副作用**：源文件原地修改，备份保留为 sibling `.yaml.backup-{ts}`（含明文 key，自动 chmod 0o600）。YAML 注释、字段顺序、multi-document 结构在 safe_load+safe_dump 处理后会丢失，命令运行时会 stderr 警告。
