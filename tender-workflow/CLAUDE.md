# CLAUDE.md

本文件为 Claude Code 提供项目上下文和工作指引。

## 项目概述

Tender Workflow 是一个 AI 辅助招投标文件生成系统，采用**四角色架构**：

| 角色 | Skill | 服务对象 | 功能 | 状态 |
|------|-------|---------|------|------|
| 策划者 | **tpl** (Tender Planner) | 甲方 | 将产品功能转换为招标技术规格与评标办法（无控标痕迹） | ✅ v2.0 已完成 |
| 分析者 | **taa** (Tender Analysis Assistant) | 乙方 | 分析招标文件、生成投标大纲（仅技术部分） | ✅ v2.4.0 已完成 |
| 撰稿者 | **taw** (Tender Article Writer) | 乙方 | 根据大纲和知识库撰写章节内容，支持并行写作、图文共生模式（AI 驱动图片匹配）和 MCP 搜索工具增强 | ✅ v3.0.0 已完成 |
| 审核者 | **trv** (Tender Reviewer) | 甲方+乙方 | 多维度审核各阶段产出物，支持 AI 驱动智能修订 | ✅ v1.5.0 已实现 |

## 目录结构

```
tender-workflow/
├── skills/                 # 所有 Skill 直接存放于此（非软链接）
│   ├── tpl/                        # 策划者：招标技术规格与评标办法
│   │   ├── SKILL.md
│   │   ├── prompts/                # anti_control / level_rules / technical / scoring
│   │   └── templates/              # government / finance / soe / enterprise
│   │
│   ├── taa/                        # 分析者：招标分析 + 大纲生成
│   │   ├── SKILL.md
│   │   ├── prompts/                # analysis / outline / phase0_params / phase2_instructions
│   │   └── tools/
│   │       ├── indexer_v2.py       # Product V2 三层索引生成器
│   │       └── docx_outline_template.py
│   │
│   ├── taw/                        # 撰稿者：章节内容撰写
│   │   ├── SKILL.md
│   │   ├── prompts/
│   │   │   ├── article_core.yaml           # 全局规则、角色定义、输出格式
│   │   │   ├── article_templates/          # 章节模板（business/technical/service/commitment）
│   │   │   ├── chapter_type_matcher.yaml   # 章节类型语义匹配
│   │   │   ├── chapter_image_quota.yaml    # 图片配额策略（h3_allocation_rules/matching_priority 已废弃）
│   │   │   ├── image_guidelines.yaml       # 图文共生护栏规则（章节上限/去重/无KB兜底）
│   │   │   # 注：AI 生图模型注册表实际由 ai-image plugin 提供（ai-image/skills/gen/prompts/ai_image_models.yaml）
│   │   │   ├── writing_brief_template.yaml # 并行写作蓝图格式规范（含 image_plan）
│   │   │   └── parallel_writer_agent.yaml  # 并行写作子智能体提示模板（含 image_plan）
│   │   └── tools/
│   │       ├── docx_writer.py              # DOCX 输出
│   │       └── kb_indexer.py               # Local-KnowledgeBase 目录索引生成器
│   │   # AI 生图通过 ai-image plugin（slash /ai-image:gen 或自然语言）
│   │   # draw.io 图表通过 drawio plugin（slash /drawio:draw 或自然语言）
│   │
│   ├── trv/                        # 审核者：多维度审核
│   │   ├── SKILL.md
│   │   └── prompts/                # completeness / compliance / scoring_alignment / risk_check
│   │
│   └── twc/                        # 配置管理
│       └── SKILL.md
│
├── Local-KnowledgeBase/              # 全 Markdown 知识库（v3.0 新格式）
│   ├── 技术方案-XXX/                   # 每个文档一个目录
│   │   ├── *.md                        # 主文档（.md），内嵌 ![](images/HASH.jpg)
│   │   ├── images/                     # 图片目录（可选）
│   │   ├── content_list_v2.json        # 内容索引
│   │   └── layout.json                 # 布局元数据
│   └── .index/
│       └── kb_catalog.yaml             # 自动生成目录索引（kb_indexer.py 产出）
│
├── tools/                          # 工具脚本
│   └── tw_config.py                # 统一配置管理工具（CLI + Python import）
│                                   # (AnythingLLM MCP 已抽到独立 plugin anythingllm-mcp)
│
└── docs/                           # 文档
    ├── data-format.md              # 各阶段产出物数据格式规范
    ├── product-index-v2-usage.md   # Product V2 三层索引使用指南
    ├── ai-image-generation.md      # AI 图片生成功能文档
    └── anythingllm-integration.md  # AnythingLLM 集成文档
```

## 关键约束

- **taw 与 taa 解耦** — taw 通过读取 taa 的 Markdown 产出物工作，不直接调用 taa 代码
- **纯 CLI/Skill 模式** — 无 Web 界面
- **知识库检索** — taw v3.0 采用 Local-KnowledgeBase Markdown 图文共生检索；无向量数据库

## 统一配置系统

**配置文件**：`~/.config/tender-workflow/config.yaml`（唯一配置文件）

旧路径 `~/.config/taw/config.yaml` 和 `~/.config/taa/config.yaml` 已废弃。

**管理命令**：
```bash
/twc setup              # 交互式首次配置向导
/twc show [skill]       # 查看当前配置
/twc set <key> <value>  # 设置配置项
/twc models [provider]  # 列出 AI 生图模型（ark/dashscope/gemini）
/twc validate           # 健康检查
/twc migrate            # 迁移旧配置
```

**配置工具**：`skills/twc/tools/tw_config.py`（供 SKILL.md 调用）
```bash
python3 skills/twc/tools/tw_config.py get taw localkb.path    # 获取值
python3 skills/twc/tools/tw_config.py set localkb.path /data  # 设置值
python3 skills/twc/tools/tw_config.py show                     # 显示全部配置
```

**配置解析优先级**：CLI 参数 > 环境变量 > 统一配置(skill 节) > 统一配置(全局节) > 默认值

## 常用命令

### 使用 Skills

```bash
# 策划者：生成招标技术规格与评标办法 (甲方)
/tpl <产品功能清单> [--project <项目概述>] --template <行业> [--level <级别>] [--no-scoring]
# 示例: /tpl features.txt --template government
# 示例: /tpl features.txt --project overview.txt --template finance --level detailed
# 示例: /tpl --kb --template soe --level brief
# 示例: /tpl features.txt --kb --template enterprise --no-scoring
# 输出: output/tpl/技术规格与评标办法_<project>_<timestamp>.docx

# 分析者：分析招标文件 (乙方)
/taa <招标文件.pdf>
/taa <招标文件.pdf> --product <产品能力说明书.xlsx|.md>  # 精确评估
/taa <招标文件.pdf> --vendor "博云"                       # 指定厂商
/taa <招标文件.pdf> --anythingllm-workspace "product-kb"  # 指定 AnythingLLM workspace slug
# 输出: output/招标分析报告_*.md + output/投标文件大纲_*.docx

# 撰稿者：撰写章节内容 (乙方)
/taw <大纲.docx> --chapter <章节号> [--search-tool <mcp|websearch|auto>] [--image-source <auto|local|drawio|ai|web|placeholder>] [--image-provider <ark|dashscope|gemini>] [--l2-words <N>] [--l3-words <N>] [--l4-words <N>] [--l5-words <N>] [--l2-images <N>] [--l3-images <N>]
# 示例：/taw output/大纲.docx --chapter 1.3 --search-tool mcp
# 示例：/taw output/大纲.docx --chapter 1.3 --image-source drawio  # 使用 draw.io 生成图表
# 示例：/taw output/大纲.docx --chapter 1.3 --image-source ai --image-provider gemini  # 指定 AI 生图供应商
# 示例：/taw output/大纲.docx --chapter 1.3 --l2-words 6000 --l3-words 1200  # 自定义字数

# 审核者：多维度审核
/trv <文件> --type <审核类型> [--reference <参考文件>] [--level <级别>] [--focus <维度>] [--revise-docx] [--revise-scope <must|all>]
# 审核类型: tender_doc | analysis | outline | chapter | full_bid
```

### 知识库管理

```bash
# KB 目录索引（Local-KnowledgeBase 格式，v3.0 推荐）
python skills/taw/tools/kb_indexer.py --scan                              # 扫描默认路径
python skills/taw/tools/kb_indexer.py --scan --kb-path /path/to/Local-KnowledgeBase  # 指定路径
/taw --build-kb-index                                                             # 通过 skill 触发

# 或通过 skill 触发
/taw --build-kb-index                      # 扫描 Local-KnowledgeBase 目录，生成 kb_catalog.yaml 索引并退出
/taa --build-index                         # 构建产品能力索引（taa）
```

### 关键路径

- **Skill 代码**: `skills/tpl/`、`skills/taw/`、`skills/trv/`、`skills/taa/`、`skills/twc/`
- **知识库（v3.0）**: `Local-KnowledgeBase/` (全 Markdown 格式，每个文档一个目录，含主文档 .md + images/)
- **产出物**: `output/` (taa 产出)、`drafts/` (taw 产出)
- **数据格式规范**: `docs/data-format.md`

## 知识库结构

### Local-KnowledgeBase 格式（v3.0 推荐）

采用**全 Markdown + 图文共生**架构，图片内嵌于文档段落中，AI 从上下文自然判断图片相关性：

```
Local-KnowledgeBase/                    # 全 Markdown 知识库
├── 技术方案-ACP平台架构说明/
│   ├── *.md                              # 主文档（.md，索引器自动发现）
│   ├── images/                           # 图片目录（可选）
│   ├── content_list_v2.json              # 内容索引
│   └── layout.json                       # 布局元数据
└── ...（最多 ~200 个目录）
```

目录索引文件（`Local-KnowledgeBase/.index/kb_catalog.yaml`，由 `kb_indexer.py` 生成）：
```yaml
generated_at: 2026-04-03T10:00:00
entries:
  - dir: 技术方案-ACP平台架构说明
    file: full.md
    title: ACP 平台架构说明
    category: 技术方案
    headings: [平台概述, 架构设计, 核心组件, 部署模式]
    summary: ACP 容器云平台整体架构，涵盖计算/网络/存储/安全四层
```

## 开发备忘

- taw 读取 taa 分析报告中的 M2(技术要求)、M4(评分标准)、M7(投标策略) 作为输入
- taw v3.0 采用**图文共生**架构：AI 读取 KB Markdown 段落时自然看到内嵌的 `![](images/HASH.jpg)` 引用，从上下文判断图片相关性，无需正则/评分公式
- 章节输出格式：Markdown 或 DOCX，遵循中文排版规范
- tpl 执行反控标自检（品牌残留/分布均衡），trv 负责深度审核（实质合规性）
- M1-M7 为 taa 分析模块编号，tpl v2.0 不再使用 M1-M6 章节编号

## 变更记录

各版本详细变更说明（tpl/taa/taw/trv 各版本核心变更、新增文件、向后兼容性等）见 [`docs/CHANGELOG.md`](docs/CHANGELOG.md)。
