# AI 图片生成快速参考

## 一分钟快速开始

### 1. 配置 API keys（一次性）

通过 ai-image plugin 的统一配置：

```bash
/ai-image:setup                         # 交互式向导（推荐）
/ai-image:set api_keys.ark <key>        # 火山方舟（推荐）
/ai-image:set api_keys.dashscope <key>  # 阿里云
/ai-image:set api_keys.gemini <key>     # Google Gemini
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

```bash
/ai-image:models                # 13 provider 全表
/ai-image:models <provider>     # 单 provider 详情
```

切换默认供应商：`/ai-image:set ai_image.default_provider <ark|dashscope|gemini|...>`
切换某 provider 的默认模型：`/ai-image:set ai_image.models.<provider> <model_id>`

## 调用底层

通过 `Skill(skill="ai-image:gen")` 触发，或直接调用 ai-image plugin 的 Python 脚本：

```bash
# 解析 ai-image plugin 的 SKILL_DIR 后：
python3 "$AI_IMAGE_DIR/scripts/image_gen.py" "<prompt>" \
  --aspect_ratio 16:9 --image_size 2K -o <output_dir>
```

v1.0.0 已删除 `image-gen` bin 入口（cross-agent 兼容性），所有调用走 SKILL.md 自然语言或 Skill() 显式触发。

## 配置迁移

如 `~/.config/tender-workflow/config.yaml` 仍包含 `api_keys` / `ai_image` 块，运行 `/ai-image:migrate` 把这两个块整理到 ai-image plugin 的统一位置（备份原文件，保留其他键）。

## 文档链接

- 详细文档：[`docs/ai-image-generation.md`](./ai-image-generation.md)
- ai-image plugin SKILL.md：`<presales-skills>/ai-image/skills/gen/SKILL.md`
