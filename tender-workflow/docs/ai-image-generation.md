# AI 图片生成

taw 在章节配图时调用 ai-image plugin；AI 生图能力由 ai-image plugin 提供，taw 不持有 API keys。

## 在 taw 中的用法

通过 `--image-source` 参数选择图片来源：

| 参数 | 说明 | 失败行为 |
|------|------|---------|
| `--image-source auto` | 按 H3 子节上下文自动选择最合适来源 | 逐级降级 |
| `--image-source local` | 本地知识库图片（图文共生匹配） | 占位符 |
| `--image-source drawio` | draw.io 生成图表 | 占位符 |
| `--image-source ai` | AI 生图（调用 ai-image plugin） | 占位符 |
| `--image-source web` | 互联网下载图片 | 占位符 |
| `--image-source placeholder` | 占位符（默认） | - |

## 配置（在 Claude 会话中说）

API keys、默认 provider、模型注册表均由 ai-image plugin 管理。直接用自然语言告诉 Claude，它会调用 ai-image plugin 完成实际工作：

| 你想做什么 | 说什么 |
|------|------|
| 首次配置 | "配置 ai-image" |
| 设置某 provider 的 API key | "设置 ai-image api_keys.\<provider\> 为 \<key\>" |
| 看某 provider 的可用模型 | "列出 ai-image 模型" / "列出 ark 模型" |
| 验证 API key 配置 | "验证 ai-image API key" |
| 切换默认 provider | "把 ai-image 默认 provider 改成 \<gemini / ark / dashscope\>" |
| 把旧 tw 配置合并到 ai-image plugin | "迁移 ai-image 配置" |

> 配置文件位置：`~/.config/presales-skills/config.yaml`，由 ai-image plugin 自包含读取。

详细的供应商对比、模型选型、自定义模型等请见 ai-image plugin 的 SKILL.md（开发者参考）。
