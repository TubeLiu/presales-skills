# AI 图片生成快速参考

## 一分钟快速开始

### 1. 配置 API keys（一次性）

通过 ai-image plugin 的统一配置（自然语言触发，由 Claude 调用 plugin 的 setup 流程）：

```text
对 Claude 说："配置 ai-image"                          # 交互式向导（推荐）
对 Claude 说："设置 ai-image api_keys.ark 为 <key>"    # 火山方舟（推荐）
对 Claude 说："设置 ai-image api_keys.dashscope 为 <key>"  # 阿里云
对 Claude 说："设置 ai-image api_keys.gemini 为 <key>"     # Google Gemini
```

或直接运行底层脚本（解析 ai-image plugin 的 SKILL_DIR 后）：

```bash
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" setup
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" set api_keys.ark <key>
```

配置存储于 `~/.config/presales-skills/config.yaml`，由 ai-image plugin 管理。taw 不再持有 API keys。

### 2. 在 taw 中触发 AI 生图

```bash
# 自动模式（按 H3 子节上下文智能选择图片来源）
/taw output/大纲.docx --chapter 1.3 --image-source auto

# 显式指定 AI 生图
/taw output/大纲.docx --chapter 1.3 --image-source ai

# 临时切换供应商（覆盖 ai-image plugin 的默认）
/taw output/大纲.docx --chapter 1.3 --image-source ai --image-provider gemini
```

## 图片来源参数

| 参数 | 说明 | 失败行为 |
|------|------|---------|
| `--image-source auto` | 按 H3 上下文智能选择 | 逐级降级 |
| `--image-source local` | 本地知识库图片 | 占位符 |
| `--image-source drawio` | draw.io 图表 | 占位符 |
| `--image-source ai` | AI 生图（调用 image-gen） | 占位符 |
| `--image-source web` | 互联网下载 | 占位符 |
| `--image-source placeholder` | 占位符 | - |

## 模型注册表

自然语言（在 Claude 会话中说）或直接运行底层脚本：

```text
对 Claude 说："列出 ai-image 模型"               # 13 provider 全表
对 Claude 说："列出 ai-image <provider> 的模型"  # 单 provider 详情
```

```bash
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" models             # 全表
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" models <provider>  # 单 provider
```

切换默认供应商 / 默认模型：

```bash
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" set ai_image.default_provider <ark|dashscope|gemini|...>
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" set ai_image.models.<provider> <model_id>
```

## 调用底层

通过 `Skill(skill="ai-image:gen")` 触发，或直接调用 ai-image plugin 的 Python 脚本：

```bash
# 解析 ai-image plugin 的 SKILL_DIR 后：
python3 "$AI_IMAGE_DIR/scripts/image_gen.py" "<prompt>" \
  --aspect_ratio 16:9 --image_size 2K -o <output_dir>
```

v1.0.0 已删除 `image-gen` bin 入口（cross-agent 兼容性），所有调用走 SKILL.md 自然语言或 Skill() 显式触发。

## 配置迁移

如 `~/.config/tender-workflow/config.yaml` 仍包含 `api_keys` / `ai_image` 块，对 Claude 说"迁移 ai-image 配置"（或直接运行 `python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" migrate`），把这两个块整理到 ai-image plugin 的统一位置（备份原文件，保留其他键）。

## 文档链接

- 详细文档：[`docs/ai-image-generation.md`](./ai-image-generation.md)
- ai-image plugin SKILL.md：`<presales-skills>/ai-image/skills/gen/SKILL.md`
