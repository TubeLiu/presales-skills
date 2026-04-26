# AI 图片生成快速参考

> 本文档面向最终用户。所有 ai-image 操作都通过自然语言交给 Claude，
> Claude 会理解意图后调用 ai-image plugin 完成实际工作——你不需要自己跑脚本。

## 一分钟快速开始

### 1. 配置 API keys（一次性）

在 Claude 会话中直接说：

- "配置 ai-image" — 启动交互式向导（推荐首次使用）
- "设置 ai-image api_keys.ark 为 \<key\>" — 火山方舟（推荐）
- "设置 ai-image api_keys.dashscope 为 \<key\>" — 阿里云通义万相
- "设置 ai-image api_keys.gemini 为 \<key\>" — Google Gemini

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
| `--image-source ai` | AI 生图（调用 ai-image plugin） | 占位符 |
| `--image-source web` | 互联网下载 | 占位符 |
| `--image-source placeholder` | 占位符 | - |

## 模型注册表 / 切换默认

在 Claude 会话中直接说：

- "列出 ai-image 模型" — 13 provider 全表
- "列出 ai-image \<provider\> 的模型" — 单 provider 详情
- "切换 ai-image 默认 provider 为 \<ark | dashscope | gemini | ...\>"
- "切换 ai-image \<provider\> 的默认模型为 \<model_id\>"

## 配置迁移

如 `~/.config/tender-workflow/config.yaml` 仍包含 `api_keys` / `ai_image` 块（旧 schema），对 Claude 说"迁移 ai-image 配置"——Claude 会把这两个块整理到 ai-image plugin 的统一位置（备份原文件，保留其他键）。

## 文档链接

- 详细文档：[`docs/ai-image-generation.md`](./ai-image-generation.md)
- 开发者参考（脚本与底层命令）：`ai-image/skills/gen/SKILL.md` + `scripts/ai_image_config.py --help`
