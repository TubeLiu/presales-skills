# AI 图片生成功能说明

> **版本**: taw v3.0.0 | **最后更新**: 2026-04-04

## 概述

taw 支持三个 AI 图片生成供应商：**火山方舟 Seedream**（主要）、**阿里云通义万相**（备选）、**Google Gemini**（可选）。生成专业技术图表，支持 2K-4K 分辨率。

使用 `/twc models` 查看所有可用模型，`/twc models --refresh` 联网更新模型列表。

> **v3.0 图文共生模式说明**：taw v3.0 引入了图文共生（text-image co-location）模式，图片优先从知识库 Markdown 上下文中自然获取 -- AI 读取 KB Markdown 时直接感知内嵌的图片引用，无需正则匹配或评分公式。AI 图片生成作为回退方案，用于没有知识库图片匹配的 H3 子节。本文档聚焦 AI 图片生成能力本身，图文共生模式的完整说明见 taw SKILL.md。

## 图片来源（v1.6.0+）

通过 `--image-source` 参数指定图片来源：

| 参数 | 说明 |
|------|------|
| `--image-source auto` | 自动选择（默认，按 H3 子节上下文独立选择最合适来源） |
| `--image-source local` | 本地知识库图片（Local-KnowledgeBase 文档关联图片） |
| `--image-source drawio` | draw.io 生成图表（需安装 draw.io Desktop） |
| `--image-source ai` | AI 生成图片（使用默认供应商，失败时报错并使用占位符） |
| `--image-source web` | 互联网下载图片 |
| `--image-source placeholder` | 仅使用占位符 |

> 失败时使用占位符，不自动降级到其他来源。

## 快速开始

### 1. 安装依赖

```bash
# 火山方舟 SDK（主要）
pip install volcengine-python-sdk

# 阿里云（REST API，无需额外 SDK）

# Google Gemini SDK（可选）
pip install google-genai

# 图片验证（推荐）
pip install pillow
```

### 2. 配置 API Key

**方式 1：环境变量（推荐）**

```bash
export ARK_API_KEY="sk-xxxxx"          # 火山方舟
export DASHSCOPE_API_KEY="sk-xxxxx"    # 阿里云
export GEMINI_API_KEY="xxxxx"          # Google Gemini（可选）
```

**方式 2：统一配置文件**

```bash
/twc set api_keys.ark "sk-xxxxx"
/twc set api_keys.dashscope "sk-xxxxx"
/twc set api_keys.gemini "xxxxx"
```

或直接编辑 `~/.config/tender-workflow/config.yaml`：

```yaml
api_keys:
  ark: "sk-xxxxx"
  dashscope: "sk-xxxxx"
  gemini: "xxxxx"

ai_image:
  default_provider: ark                    # 默认供应商（ark/dashscope/gemini）
  size: 2048x2048
  max_retries: 2
  timeout: 60
  models:
    ark: doubao-seedream-5-0-260128
    dashscope: qwen-image-2.0-pro
    gemini: gemini-2.5-flash-image
```

### 3. 使用示例

```bash
# 使用 AI 生成图片（使用默认供应商）
/taw output/ --chapter 1.3 --image-source ai

# 指定 AI 生图供应商
/taw output/ --chapter 1.3 --image-source ai --image-provider gemini

# draw.io 生成图表
/taw output/ --chapter 1.3 --image-source drawio

# 自动模式（默认，智能选择图片来源）
/taw output/ --chapter 1.3 --image-source auto

# 使用占位符（默认行为，不指定 --image-source）
/taw output/ --chapter 1.3
```

## API 供应商

### 查看所有可用模型

```bash
/twc models              # 查看全部
/twc models ark          # 仅火山方舟
/twc models gemini       # 仅 Gemini
/twc models --refresh    # 联网更新模型列表
```

### 火山方舟 Seedream（主要）

- **默认模型**：`doubao-seedream-5-0-260128`（Seedream 5.0 Lite）
- **分辨率**：原生 2K，AI 增强 4K
- **费用**：~¥0.25/张
- **文档**：https://www.volcengine.com/docs/82379/1541523

### 阿里云通义万相（备选）

- **默认模型**：`qwen-image-2.0-pro`（Qwen Image 2.0 Pro）
- **分辨率**：2K（2048x2048）
- **费用**：~$0.075/张
- **文档**：https://help.aliyun.com/zh/model-studio/

### Google Gemini（可选）

- **默认模型**：`gemini-2.5-flash-image`（Gemini 2.5 Flash Image）
- **分辨率**：最高 4K（4096x4096）
- **费用**：~$0.039/张
- **SDK**：`pip install google-genai`
- **特点**：原生生图、图片编辑、角色一致性、对话式优化

Gemini 支持两类模型：
- **gemini-\* 系列**（generateContent API）：多模态生图，支持 4K，推荐
- **imagen-\* 系列**（generate_images API）：专用生图，1K 分辨率

### 切换默认模型

```bash
# 查看可选模型
/twc models

# 切换默认模型
/twc set ai_image.models.ark doubao-seedream-4-0-250828
/twc set ai_image.models.gemini gemini-3.1-flash-image-preview

# 切换默认供应商
/twc set ai_image.default_provider gemini
```

## 供应商选择机制

1. **使用默认供应商**：`default_provider` 指定的供应商（默认：ark）
   - 可通过 `--image-provider` 参数临时覆盖
2. **默认供应商失败**：报错并使用占位符，不自动降级到其他供应商
3. **未配置 API Key**：使用占位符

## 提示词设计

所有提示词使用中文，确保风格统一：
- **配色方案**：深蓝色 #1E3A8A、浅蓝色 #60A5FA、灰色 #6B7280
- **标准图标**：使用标准 IT 架构图标和流程图符号
- **文字标注**：关键信息清晰可辨，字体 14-16pt
- **投标规范**：符合投标文件技术图纸规范
- **背景**：纯白色 #FFFFFF

## 图片质量验证

生成的图片会自动验证：
- 文件大小 > 10KB
- 分辨率 ≥ 512x512（目标 2048x2048）
- 格式正确（PNG）

验证失败会自动重试，仍失败则使用占位符。

## 命令行测试工具

```bash
# 生成架构图
python3 skills/taw/tools/ai_image_generator.py \
  --type architecture \
  --topic "容器云平台总体架构" \
  --components "基础设施层,K8s编排层,ACP平台层,业务应用层" \
  --output /tmp/test_arch.png

# 指定供应商
python3 skills/taw/tools/ai_image_generator.py \
  --type architecture \
  --topic "测试架构" \
  --components "组件1,组件2" \
  --provider gemini \
  --output /tmp/test_gemini.png
```

## 常见问题

### Q1: 如何禁用 AI 生图？

不使用 `--image-source ai` 参数即可（不指定时默认使用占位符）：
```bash
/taw output/ --chapter 1.3
```

### Q2: 如何切换默认供应商？

```bash
/twc set ai_image.default_provider dashscope
```

### Q3: API 调用失败怎么办？

默认供应商失败时使用占位符，不自动降级到其他供应商。可通过 `--image-provider` 临时切换供应商。检查步骤：

1. 检查 API Key：`/twc show` 或 `echo $ARK_API_KEY`
2. 手动测试：
   ```bash
   python3 skills/taw/tools/ai_image_generator.py \
     --type architecture --topic "测试" --components "A,B" \
     --output /tmp/test.png
   ```
3. 检查依赖：`pip list | grep volcengine` / `pip list | grep google-genai`

### Q4: Gemini 模型选哪个？

- **推荐**：`gemini-2.5-flash-image`（稳定版，4K，$0.039/张）
- **快速**：`gemini-3.1-flash-image-preview`（预览版，文字渲染优化）
- **专业**：`gemini-3-pro-image-preview`（预览版，工作室级 4K）

使用 `/twc models gemini` 查看完整列表。

## 更新日志

### v1.9.1 (2026-04-02)

- ✅ Google Gemini 生图回归（第三供应商）
- ✅ 新增模型注册表（`ai_image_models.yaml`），集中管理所有模型元数据
- ✅ 模型 ID 可配置化（三供应商均支持通过 `/twc set` 切换）
- ✅ `/twc models` 命令查看可用模型，`/twc models --refresh` 联网更新
- ✅ Gemini 支持 gemini-* 多模态生图（generateContent API）和 imagen-* 系列

### v1.8.0 (2026-04-01)

- ✅ 并行写作架构：长章节（≥3 H3 + ≥4,500 字）自动启用并行写作

### v1.7.0 (2026-03-16)

- ✅ draw.io 集成：生成可编辑 .drawio 文件，支持导出 PNG/SVG/PDF

### v1.6.0 (2026-03-09)

- ✅ 图片生成逻辑简化：显式参数控制，删除复杂降级机制
- ❌ 删除参数：`--no-ai-image`、`--ai-only`、`--no-web-image`、`--strict-image`

### v1.4.0 (2026-03-08)

- ✅ 初始 AI 图片生成：火山方舟 Seedream 5.0 Lite + 阿里云通义万相
