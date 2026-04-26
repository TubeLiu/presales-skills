# AI 图片生成

taw 在章节配图时通过 `Skill(skill="ai-image:gen")` 调用 ai-image plugin；AI 生图能力由 ai-image plugin 提供，taw 不持有 API keys。

## 在 taw 中的用法

通过 `--image-source` 参数选择图片来源：

| 参数 | 说明 | 失败行为 |
|------|------|---------|
| `--image-source auto` | 按 H3 子节上下文自动选择最合适来源 | 逐级降级 |
| `--image-source local` | 本地知识库图片（图文共生匹配） | 占位符 |
| `--image-source drawio` | draw.io 生成图表 | 占位符 |
| `--image-source ai` | AI 生图（通过 Skill(skill="ai-image:gen") 调用 ai-image plugin） | 占位符 |
| `--image-source web` | 互联网下载图片 | 占位符 |
| `--image-source placeholder` | 占位符（默认） | - |

`ai` 模式底层通过 Skill 工具调用 ai-image plugin，或直接调用 Python 脚本：

```bash
# 解析 ai-image plugin 的 SKILL_DIR 后：
python3 "$AI_IMAGE_DIR/scripts/image_gen.py" "<prompt>" \
  --aspect_ratio 16:9 --image_size 2K -o <output_dir>
```

v1.0.0 已删除 `image-gen` bin 入口（cross-agent 兼容性，commit c983037）；底层脚本 `ai-image/skills/gen/scripts/image_gen.py` 自包含读取 `~/.config/presales-skills/config.yaml` 中的 API keys 与默认 provider。

## 配置

API keys、默认 provider、模型注册表均由 ai-image plugin 管理：

| 命令 | 说明 |
|------|------|
| `/ai-image:setup` | 交互式首次配置（写入 `~/.config/presales-skills/config.yaml`） |
| `/ai-image:models [provider]` | 查看 13 provider 的模型注册表 |
| `/ai-image:validate [provider]` | 验证 API key 配置完整性 |
| `/ai-image:set api_keys.<provider> <key>` | 设置某个 provider 的 API key |

> 如 `~/.config/tender-workflow/config.yaml` 仍包含 `api_keys` / `ai_image` 块，运行 `/ai-image:migrate` 把这两个块整理到 ai-image plugin 的统一位置。

详细的供应商对比、模型选型、自定义模型等请见 ai-image plugin 的 SKILL.md。
