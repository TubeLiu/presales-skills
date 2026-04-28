# ai-image — 统一 AI 图片生成

**中文** | [English](./README_EN.md)

`presales-skills` marketplace 的**共享 plugin**，为 solution-master / ppt-master / tender-workflow 提供统一的 AI 图片生成能力。13 后端共享一份模型注册表与配置；自带 79 个结构化提示词模板覆盖 17 类高密度视觉场景。

> 🙏 **致谢上游**：`templates/` 目录下的 79 个结构化提示词模板源自 [ConardLi/garden-skills](https://github.com/ConardLi/garden-skills) 的 gpt-image-2 项目（MIT License），覆盖 PPT slide / 信息图 / UI mockup / 学术图 / 技术图 / 海报等高密度视觉场景。本仓做了 garden-skills → presales-skills 的体例适配（路径、命名、与 ai-image plugin 集成），核心 prompt 内容沿用上游设计。LICENSE 见 [`skills/gen/templates/LICENSE-gpt-image-2`](./skills/gen/templates/LICENSE-gpt-image-2)。

---

## 核心能力

- **13 后端统一调用**：volcengine/ark · qwen/dashscope · gemini · openai · minimax · stability · bfl · ideogram · zhipu · siliconflow · fal · replicate · openrouter
- **共享模型注册表**：`prompts/ai_image_models.yaml` 定义所有 provider × model 的 ID / 价格 / 分辨率 / 特性，新增模型只改一处
- **79 个结构化模板（17 类）**：自动匹配高密度视觉场景，按模板槽位逐项确认后再生图，比自由 prompt 输出稳定得多
- **OpenAI 后端独家**：透明背景 PNG（logo / icon 抠图）、webp/jpeg 自定义压缩输出、图像编辑（inpainting，可带 mask 局部重绘）
- **统一配置**：所有 API key / 默认参数集中在 `~/.config/presales-skills/config.yaml`，三个主 plugin 共用，不需重复配

## Slash 入口

| 触发方式 | 形式 |
|---|---|
| Claude Code canonical | `/ai-image:gen "现代简约风的容器云架构示意"` |
| Codex / Cursor / OpenCode 短形式 alias | `/image-gen "..."` |
| 自然语言 auto-trigger | "生成图片：xxx" / "做一张配图" / "画一张架构图" / "generate image" / "make illustration" |
| 结构化场景 auto-trigger | "做一张 Bento grid 信息图" / "PPT 配图" / "ER 图" / "学术图形摘要" 等 → 自动走 `templates/` 模板 |
| 图像编辑 | "把这张图的背景换成蓝天白云" / "局部重绘 / 移除元素" → 自动走 OpenAI inpainting（`--mode edit`） |
| 管理子命令 | "配置 ai-image" / "首次配置" / "validate api key" / "list image models" / "add custom model" |

## 17 类内置模板速查

| 类别 | 用途 | 适用主 plugin |
|---|---|---|
| `slides-and-visual-docs/` | 高密度讲解 slide / 教育 slide / 政策风 slide / visual report | ppt-master |
| `infographics/` | Bento grid / KPI dashboard / 对比信息图 / 步骤图 | solution-master / ppt-master |
| `ui-mockups/` | 聊天界面 / 短视频封面 / 直播带货 UI / 社交 UI | tender-workflow / solution-master |
| `academic-figures/` | 图形摘要 / 神经网络架构 / 论文图表 / 方法流程图 | solution-master |
| `technical-diagrams/` | ER 图 / 流程图 / 时序图 / 状态机 / 系统架构 / 网络拓扑（PNG，非矢量；可编辑用 drawio）| solution-master |
| `maps/` | 食物地图 / 旅游路线 / 城市插画地图 / 门店分布 | 通用 |
| `poster-and-campaigns/` | 海报、活动 banner | 通用 |
| `product-visuals/` | 产品摄影、棚拍 | 通用 |
| `branding-and-packaging/` | 品牌包装 | 通用 |
| `portraits-and-characters/` | 肖像、角色图 | 通用 |
| `avatars-and-profile/` | 头像、profile picture | 通用 |
| `editing-workflows/` | 图像编辑工作流 | 通用 |
| `grids-and-collages/` | 网格 / 拼贴 | 通用 |
| `scenes-and-illustrations/` | 场景插画 | 通用 |
| `storyboards-and-sequences/` | 漫画分镜 / 连环序列 | 通用 |
| `typography-and-text-layout/` | 字体排版 / 文字版面 | 通用 |
| `assets-and-props/` | 道具、素材 | 通用 |

每个模板 `.md` 文件含视觉层结构 + `{argument name="..." default="..."}` 槽位 + 缺失字段提问优先级。

## 配置

> **安装**：见仓库根 [README.md#安装](../README.md#安装)。

装好后用自然语言配置：

```
> 配置 ai-image                 # 交互式首次配置向导
> 设置 ai-image api_keys.ark 为 sk-xxx
> 验证 ai-image API key         # 健康检查
> 列出 ai-image 模型            # 13 后端的完整注册表
> 迁移旧 ai-image 配置           # 合并旧 ~/.config/{solution-master,tender-workflow}/config.yaml
```

或纯 CLI（power user）—— 先按 SKILL.md §路径自定位 解析 `$AI_IMAGE_DIR`：

```bash
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" setup
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" set api_keys.ark <key>
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" validate
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" models [provider]
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" add-model <provider> <yaml-snippet>
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" migrate
```

**配置文件**：`~/.config/presales-skills/config.yaml` —— 字段：`api_keys.<provider>` / `ai_image.default_provider` / `ai_image.default_size` / `ai_image.default_aspect_ratio`。`models-user.yaml` 同目录下,用户自定义模型放这里(走 `add-model` 命令)。

## 跨 plugin 调用

solution-master / ppt-master / tender-workflow 在自己的 SKILL.md 里调用 ai-image 时,**用 installed_plugins.json bootstrap** 解析 ai-image plugin 路径(仅 plugin 名替换为 `ai-image`),然后:

```bash
python3 "$AI_IMAGE_DIR/scripts/image_gen.py" "<prompt>" --aspect_ratio 16:9 --image_size 1K -o /path/to/output/
```

详见各主 plugin SKILL.md 的"跨 plugin 调用"模板段。

## 使用示例

```
> 生成一张图：现代简约风的容器云架构示意
> 用 ark 生成一张 K8s 网络拓扑图
> /ai-image:gen "futuristic cloud platform dashboard, hi-tech aesthetic"
> 生成透明背景的狐狸 logo                    # OpenAI 后端独家
> 把这张图的背景换成蓝天白云（要原图路径）       # OpenAI inpainting
> 做一张 Bento grid 信息图，对比 5 个云厂商    # 自动走 infographics/ 模板
> 做一张 ER 图：用户 / 订单 / 商品 / 库存       # 自动走 technical-diagrams/ 模板
```

## 不处理

- **视频生成** —— 本 plugin 仅图片;视频另议
- **ASCII art** —— 走纯文本工具,不走图片生成

## 项目结构

```
ai-image/
├── .claude-plugin/plugin.json       # plugin metadata
├── skills/gen/
│   ├── SKILL.md                     # 主入口 / 路径自定位 / 工作流
│   ├── setup.md                     # 配置 wizard
│   ├── requirements.txt             # Python 依赖
│   ├── prompts/
│   │   └── ai_image_models.yaml     # 13 后端 × 模型注册表（统一）
│   ├── templates/                   # 79 模板，17 类（vendor from garden-skills MIT）
│   │   ├── slides-and-visual-docs/
│   │   ├── infographics/
│   │   ├── ui-mockups/
│   │   ├── academic-figures/
│   │   ├── technical-diagrams/
│   │   └── ...（共 17 类）
│   └── scripts/
│       ├── _ensure_deps.py          # 自动 pip install
│       ├── ai_image_config.py       # 配置 CRUD CLI
│       ├── image_gen.py             # 主入口（被 SKILL.md / 主 plugin 调用）
│       └── image_backends/          # 13 后端各自的实现
└── tests/                           # ai-image 自家单元测试
    ├── test_config_size_validation.py
    ├── test_ensure_deps_lock.py
    └── test_sanitize_error.py
```

## 与其他 plugin 的关系

| 主 plugin | 用 ai-image 做什么 |
|---|---|
| **solution-master** | 章节配图(架构图走 drawio,概念图 / 截图走 ai-image);结构化场景自动走 templates/ |
| **ppt-master** | PPT 每页配图;Bento grid / 政策风 slide 等自动走 templates/ |
| **tender-workflow taw** | 投标章节配图,按 H3 子节上下文挑 ai-image / drawio / 占位符 |

三个主 plugin 都把 ai-image 列为**必需依赖**;不装 ai-image 时配图能力降级到占位符。

## 第三方组件

`templates/` 目录下的提示词模板源自 [ConardLi/garden-skills](https://github.com/ConardLi/garden-skills) 的 gpt-image-2 项目(MIT License)。详细借用清单与原项目 LICENSE 见 [`skills/gen/templates/LICENSE-gpt-image-2`](./skills/gen/templates/LICENSE-gpt-image-2)。
