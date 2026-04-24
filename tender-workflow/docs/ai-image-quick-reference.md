# AI 图片生成功能快速参考

> **版本**: taw v3.0.0 | **最后更新**: 2026-04-04

---

## 一分钟快速开始

### 1. 安装依赖
```bash
pip install volcengine-python-sdk pillow    # 火山方舟（主要）
pip install google-genai                     # Google Gemini（可选）
```

### 2. 配置 API Key
```bash
export ARK_API_KEY="sk-xxxxx"       # 火山方舟
export GEMINI_API_KEY="xxxxx"       # Google Gemini（可选）
```

### 3. 使用
```bash
# 自动模式（按 H3 子节上下文智能选择图片来源）
/taw output/ --chapter 1.3 --image-source auto

# 显式指定图片来源
/taw output/ --chapter 1.3 --image-source local         # 本地知识库图片
/taw output/ --chapter 1.3 --image-source ai          # AI 生图
/taw output/ --chapter 1.3 --image-source drawio       # draw.io 图表
/taw output/ --chapter 1.3 --image-source web          # 互联网下载
/taw output/ --chapter 1.3 --image-source placeholder  # 占位符

# 不指定 --image-source 时默认使用占位符
/taw output/ --chapter 1.3
```

---

## 图片来源参数

| 参数 | 说明 | 失败行为 |
|------|------|---------|
| `--image-source auto` | 按 H3 上下文智能选择 | 逐级降级 |
| `--image-source local` | 本地知识库图片 | 占位符 |
| `--image-source drawio` | draw.io 图表 | 占位符 |
| `--image-source ai` | AI 生图（使用默认供应商） | 占位符 |
| `--image-source web` | 互联网下载 | 占位符 |
| `--image-source placeholder` | 占位符 | - |

---

## API 供应商

查看完整模型列表：`/twc models`
联网更新模型列表：`/twc models --refresh`

| 提供商 | 默认模型 | 最大分辨率 | 费用 | 环境变量 |
|--------|---------|-----------|------|----------|
| 火山方舟 | doubao-seedream-5-0-260128 | 4K | ~¥0.25/张 | `ARK_API_KEY` |
| 阿里云 | qwen-image-2.0-pro | 2K | ~$0.075/张 | `DASHSCOPE_API_KEY` |
| Gemini | gemini-2.5-flash-image | 4K | ~$0.039/张 | `GEMINI_API_KEY` |

切换默认模型：`/twc set ai_image.models.<provider> <model_id>`
切换默认供应商：`/twc set ai_image.default_provider gemini`

---

## 配置文件

`~/.config/tender-workflow/config.yaml`:
```yaml
api_keys:
  ark: "sk-xxxxx"
  dashscope: "sk-xxxxx"
  gemini: "xxxxx"
ai_image:
  default_provider: ark                  # 默认供应商（ark/dashscope/gemini）
  models:
    ark: doubao-seedream-5-0-260128
    dashscope: qwen-image-2.0-pro
    gemini: gemini-2.5-flash-image
```

---

## 测试命令

```bash
python3 .claude/skills/taw/tools/ai_image_generator.py \
  --type architecture \
  --topic "容器云平台总体架构" \
  --components "基础设施层,K8s编排层,ACP平台层,业务应用层" \
  --output /tmp/test.png

# 指定供应商
python3 .claude/skills/taw/tools/ai_image_generator.py \
  --type architecture --topic "测试" --components "A,B" \
  --provider gemini --output /tmp/test_gemini.png
```

---

## 常见问题

**Q: 如何禁用 AI 生图？**
不使用 `--image-source ai` 参数即可（不指定时默认占位符）。

**Q: 如何切换默认供应商？**
`/twc set ai_image.default_provider dashscope`

**Q: API 调用失败怎么办？**
默认供应商失败时报错并使用占位符，不自动降级到其他供应商。可通过 `--image-provider` 临时切换供应商。

**Q: Gemini 选哪个模型？**
运行 `/twc models gemini` 查看完整列表。推荐 `gemini-2.5-flash-image`（稳定，4K，$0.039/张）。

---

## 文档链接

- 详细文档：`docs/ai-image-generation.md`
- SKILL.md：`.claude/skills/taw/SKILL.md`
- 模型注册表：`.claude/skills/taw/prompts/ai_image_models.yaml`
