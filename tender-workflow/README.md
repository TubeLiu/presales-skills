# Tender Workflow — AI 辅助招投标工作流

> 从招标文件到标书成稿的完整 AI 辅助解决方案

---

## 作为 Claude Code plugin 安装

tender-workflow 现作为 `presales-skills` umbrella marketplace 的成员 plugin 分发：

```
/plugin marketplace add Alauda-io/presales-skills     # 或本地路径 /path/to/presales-skills
/plugin install drawio@presales-skills
/plugin install ai-image@presales-skills
/plugin install anythingllm-mcp@presales-skills       # 可选：知识库语义搜索，不装则降级
/plugin install tender-workflow@presales-skills
```

安装后 `/tpl` `/taa` `/taw` `/trv` `/twc` 五个命令可在任意目录调用。AnythingLLM 语义搜索由独立共享 plugin `anythingllm-mcp` 提供（统一 MCP server 名 `anythingllm`，solution-master / tender-workflow 共用）；若未安装，taa/taw 会自动降级为本地 YAML 索引或联网检索。源码模式（直接 cd 进本目录）同样可用，下文描述的 `python skills/...` 命令仅在源码模式下直接执行。

---

## 项目概述

### 目标
构建四角色 AI 辅助招投标工作流，覆盖招标文件编写、深度分析、标书撰写、质量审核全流程。

### 核心流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            四角色招投标工作流                                  │
├─────────────┬─────────────┬─────────────┬─────────────────────────────────────┤
│   策划者     │   规划者     │   撰写者     │              审核者                  │
│   (tpl)      │   (taa)      │   (taw)      │              (trv)                   │
├─────────────┼─────────────┼─────────────┼─────────────────────────────────────┤
│  编写招标文件 │  分析招标文件 │  撰写标书章节 │      审核各阶段产出                   │
│  服务甲方    │  服务乙方    │  服务乙方    │      服务甲乙双方                     │
└─────────────┴─────────────┴─────────────┴─────────────────────────────────────┘
       ↑                                                    ↑
       └──────────────── 审核反馈 ──────────────────────────┘
```

**标准数据流**:
```
甲方：项目需求 → [tpl] → 招标文件 → [trv 审核] → 发布
                          ↓
乙方：招标文件 → [taa] → 分析报告 + 大纲 → [trv 审核] → [taw] → 章节草稿 → [trv 审核] → 完整标书
```

---

## 架构设计

```
tender-workflow/
├── skills/             # 所有 Skill 直接存放于此
│   ├── common/                   # 通用语义解析框架
│   │   └── parsers/
│   │       ├── chapter_parser.yaml       # 章节编号语义解析
│   │       └── template_matcher.yaml     # 模板名称语义匹配
│   │
│   ├── tpl/                    # ✅ 策划者：招标技术规格与评标办法 (服务甲方)
│   │   ├── SKILL.md
│   │   ├── prompts/
│   │   │   ├── anti_control.yaml   # 反控标转换规则
│   │   │   ├── level_rules.yaml    # 四级细致程度定义
│   │   │   ├── technical.yaml      # 技术规格编写规则
│   │   │   └── scoring.yaml        # 评标办法设计规则
│   │   └── templates/          # 行业模板
│   │       ├── government.yaml   # 政府行业
│   │       ├── finance.yaml      # 金融行业
│   │       ├── soe.yaml          # 央国企
│   │       └── enterprise.yaml   # 通用企业
│   │
│   ├── trv/                    # ✅ 审核者：多维度质量审核 (服务双方)
│   │   ├── SKILL.md
│   │   └── prompts/
│   │       ├── completeness.yaml     # 完整性检查
│   │       ├── compliance.yaml       # 合规性审查
│   │       ├── scoring_alignment.yaml # 评分契合度分析
│   │       └── risk_check.yaml       # 风险识别
│   │
│   ├── taa/                    # ✅ 规划者：招标分析 + 大纲生成 (服务乙方)
│   │   ├── SKILL.md
│   │   ├── prompts/
│   │   │   ├── analysis.yaml       # 7 模块分析框架
│   │   │   ├── outline.yaml        # 大纲生成框架
│   │   │   └── phase0_params.md    # Phase 0 参数处理规则
│   │   ├── templates/builtin/  # 内置行业模板
│   │   │   ├── government_it.yaml
│   │   │   ├── state_owned_enterprise.yaml
│   │   │   ├── finance.yaml
│   │   │   └── general.yaml
│   │   └── tools/
│   │       ├── indexer_v2.py           # Product V2 三层索引生成器
│   │       └── docx_outline_template.py # DOCX 大纲模板工具
│   │
│   ├── taw/                    # ✅ 撰写者：章节内容撰写 (服务乙方)
│   │   ├── SKILL.md
│   │   ├── prompts/
│   │   │   ├── article_core.yaml              # 核心模板
│   │   │   ├── chapter_type_matcher.yaml      # 章节类型语义匹配
│   │   │   ├── chapter_image_quota.yaml       # 图片配额策略
│   │   │   # 注：AI 生图模型注册表实际由 ai-image plugin 提供（ai-image/skills/gen/prompts/ai_image_models.yaml）
│   │   │   ├── writing_brief_template.yaml    # 并行写作蓝图格式规范
│   │   │   ├── parallel_writer_agent.yaml     # 并行写作子智能体提示模板
│   │   │   └── article_templates/             # 章节模板（按需加载）
│   │   │       ├── business.yaml              # 商务章节
│   │   │       ├── technical.yaml             # 技术章节
│   │   │       ├── service.yaml               # 服务章节
│   │   │       └── commitment.yaml            # 承诺章节
│   │   └── tools/
│   │       ├── docx_writer.py         # DOCX 输出
│   │       └── kb_indexer.py          # Local-KnowledgeBase 目录索引生成器
│   │   # AI 生图通过 ai-image plugin（slash /ai-image:gen 或自然语言）
│   │   # draw.io 图表通过 drawio plugin（slash /drawio:draw 或自然语言）
│   │
│   └── twc/                    # ✅ 配置管理
│       └── SKILL.md
│
├── Local-KnowledgeBase/      # 全 Markdown 知识库（v3.0 推荐，路径由配置指定）
│   ├── 技术方案-*/             # 技术文档目录（主文档 .md + images/）
│   ├── 交付方案-*/             # 交付文档目录
│   └── .index/                 # kb_catalog.yaml（自动生成目录索引）
│
├── tools/                      # 工具脚本
│   └── tw_config.py            # 统一配置管理工具（CLI + Python import）
│                               # (AnythingLLM MCP 已抽到独立 plugin anythingllm-mcp)
│
└── docs/                       # 文档
    ├── data-format.md              # 数据格式规范
    ├── product-index-v2-usage.md   # Product V2 三层索引使用指南
    ├── ai-image-generation.md      # AI 图片生成功能文档
    └── anythingllm-integration.md  # AnythingLLM 集成文档
```

---

## 四角色详解

### 角色 1: 策划者 (tpl) — 招标技术规格与评标办法生成 ✅ v2.0

**服务对象**: 甲方（招标方）
**核心任务**: 将产品功能清单转换为无控标痕迹的招标技术规格与评标办法

**🎯 核心能力**：
- ✅ **反控标转换**：术语中性化（去品牌）、指标合理化（下限表达）、需求泛化、分布均衡
- ✅ **控标点强制纳入**：标注"控标点"的条目不受压缩比影响，保留核心指标
- ✅ **行业模板差异化**：4 种行业模板（政府/金融/央国企/通用企业）
- ✅ **四级细致程度**：detailed/standard/general/brief

**使用**:
```bash
/tpl <产品功能清单> [--project <项目概述>] --template <行业> [--level <级别>] [--no-scoring]
```

**参数说明**:
- `<产品功能清单>`: 必选（或 `--kb`）。产品功能文件（.txt/.md/.xlsx/.pdf）
- `--kb`: 可选。使用知识库产品索引，可与文件输入组合
- `--project <file>`: 可选。项目概述（背景、预算、规模）
- `--template`: 必选。行业类型
  - `government`: 政府机关、事业单位（含信创/国产化要求）
  - `finance`: 银行、保险、证券（金融级安全、高可用）
  - `soe`: 中央企业、国有企业（自主可控、长期支持）
  - `enterprise`: 民营企业、外资企业（性价比、灵活性）
- `--level`: 可选，默认 `standard`。细致程度
  - `detailed`: 40-60 条要求，15-20 页（大型项目 >500 万）
  - `standard`: 15-25 条要求，8-12 页（中型项目 100-500 万）
  - `general`: 8-12 条要求，4-6 页（小型项目 50-100 万）
  - `brief`: 5-8 条要求，2-3 页（<50 万或内部参考）
- `--no-scoring`: 可选。跳过评标办法，只生成技术规格
- `-h, --help`: 显示帮助信息

**示例**:
```bash
# 政府行业标准技术规格与评标办法
/tpl features.txt --template government

# 金融行业详细技术规格，含项目背景
/tpl features.txt --project overview.txt --template finance --level detailed

# 使用知识库产品索引，简略输出
/tpl --kb --template soe --level brief

# 组合输入，只生成技术规格
/tpl features.txt --kb --template enterprise --no-scoring
```

**输出**:
```
output/tpl/
└── 技术规格与评标办法_<项目名>_<timestamp>.docx
    ├── 第一部分：技术规格与要求（9 章）
    └── 第二部分：评标办法（6 章，除非 --no-scoring）
```

**工作流程**:
Phase 0 参数解析 → Phase 1 功能分析 → Phase 2 反控标转换（核心）→ Phase 3 技术规格生成 → Phase 4 评标办法生成 → Phase 5 DOCX 输出

---

### 角色 2: 审核者 (trv) — 多维度质量审核 ✅ v1.5.0

**服务对象**: 甲方 + 乙方（招投标全流程）
**核心任务**: 对各阶段产出物进行质量把控，识别问题与风险

**使用**:
```bash
/trv <file> --type <review_type> [--reference <file>] [--level <level>] [--focus <focus>] [--revise-docx] [--revise-scope <must|all>]
```

**审核类型**:
| 类型 | 说明 | 适用场景 |
|------|------|----------|
| `tender_doc` | 招标文件审核 | 甲方编标自查、乙方合规审查 |
| `analysis` | 招标分析报告审核 | 乙方 taa 产出检查 |
| `outline` | 投标大纲审核 | 乙方大纲结构检查 |
| `chapter` | 章节草稿审核 | 乙方 taw 产出检查 |
| `full_bid` | 完整标书审核 | 投标前最终检查（大文件自动分块审核） |

**审核维度**:
- **完整性检查**: 必备要素齐全性
- **合规性审查**: 法律法规符合性
- **评分契合度**: 内容与评分标准匹配度
- **风险识别**: 废标风险、履约风险、合规风险
- **跨章节一致性**（v1.4.0，分块模式）: 数值/描述/承诺跨章节矛盾检测

**v1.4.0 大文件分块审核**：full_bid/chapter 超过 80K token 时自动启用分块模式——按章节拆分为 chunk，并行子 Agent 审核，最后执行跨章节一致性检查。

**v1.5.0 智能修订**：可通过 `--revise-docx --revise-scope <must|all>` 在审核完成后自动生成修订版 DOCX。Claude 基于审核发现动态生成修订指令（段落替换、表格修正、术语统一等），Python 工具执行通用 DOCX 操作并保留原有格式。`must`（默认）仅修订严重/重要问题，`all` 包含所有建议项。非 DOCX 输入或不支持的审核类型会自动跳过修订，不中断审核。

**参考文件映射**:
| 审核类型 | 推荐参考文件 | 用途 |
|---------|-------------|------|
| `outline` | 招标分析报告 | 对照评分标准检查大纲覆盖 |
| `chapter` | 招标分析报告 | 检查内容契合度和一致性 |
| `full_bid` | 招标文件 | 对照原始要求检查响应性 |

**输出**:
```
output/trv/
├── 审核报告_<type>_<timestamp>.md
│   ├── 审核结论（通过/有条件通过/不通过）
│   ├── 完整性检查结果
│   ├── 合规性审查结果
│   ├── 评分契合度分析
│   ├── 风险识别清单
│   └── 修改优先级建议
└── <原文件名>_修订版_<timestamp>.docx  # 启用 --revise-docx 且输入受支持时生成
```

---

### 角色 3: 规划者 (taa) — 招标分析 + 大纲生成 ✅ v2.4.0

**服务对象**: 乙方（投标方）
**核心任务**: 深度分析招标文件，生成投标大纲

**核心能力提升**：
- ✅ **v2.4.0 Phase 0 提取**（2026-04-02）：参数处理规则独立到 `prompts/phase0_params.md`，按需加载
- ✅ **v2.3.0 Context window 优化**（2026-04-01）：压缩 SKILL.md 冗余，配置外置到 YAML/MD 文件
- ✅ **v2.2.1 AnythingLLM 集成增强**（2026-03-17）：新增 `--kb-source` 参数，支持强制使用 AnythingLLM 或本地索引
- ✅ **v2.2.0 大纲简化**（2026-03-10）：仅保留技术部分，服务方案整合到技术部分末尾（1.10 和 1.11）
- ✅ **v2.1.0 AnythingLLM 集成**（2026-03-09）：支持 `--anythingllm-workspace` 参数和配置文件
- ✅ **v2.0.0 Product V2 三层索引**（2026-03-05）：L0 快速路由（~2KB）+ L1 分类索引（11 个）+ L2 完整详情（11 个），按需加载节省 70-90% token

**使用**:
```bash
# 基本用法（自动检测 AnythingLLM 或使用本地索引）
/taa <招标文件路径>

# 指定产品能力说明书（精确评估匹配度）
/taa <招标文件路径> --product <产品能力说明书.xlsx|.md>

# 指定 AnythingLLM workspace
/taa <招标文件路径> --anythingllm-workspace "产品能力库"

# 强制使用 AnythingLLM 作为产品能力来源（不可用则报错）
/taa <招标文件路径> --kb-source anythingllm

# 强制使用本地索引，跳过 AnythingLLM
/taa <招标文件路径> --kb-source local

# 指定厂商名称（默认"灵雀云"）
/taa <招标文件路径> --vendor "博云"

# 组合使用
/taa <招标文件路径> --product specs/产品能力.md --vendor "博云"

# 仅构建产品能力索引（不执行分析）
/taa --build-index --product <产品能力说明书.xlsx>

# 分析时保存索引到默认位置
/taa <招标文件路径> --product <产品能力说明书.xlsx> --save-index
```

**输出**:
```
output/
├── 招标分析报告_YYYYMMDD_HHMMSS.md    # 7 模块深度分析（M1-M7 + 行业扩展 E1-E3）
└── 投标文件大纲_YYYYMMDD_HHMMSS.docx  # 结构化大纲（仅技术部分）
```

**产品能力来源优先级**:
```
--product 指定文件（最高优先，精确评估）
    ↓ 未指定时
AnythingLLM 语义检索（M2 阶段按需查询，查询缓存机制）
    ↓ 不可用时
本地 YAML 索引（V2 三层 / V1 单文件）
    ↓ 均无时
AI 模糊评估
```

**`--kb-source` 参数**（v2.2.1 新增）:
| 参数值 | 说明 |
|--------|------|
| `auto`（默认） | 先尝试 AnythingLLM，不可用则降级到本地索引 |
| `anythingllm` | 强制使用 AnythingLLM（不可用则报错退出） |
| `local` | 强制使用本地索引，跳过 AnythingLLM 检测 |

**注意**: 若同时使用 `--product` 和 `--kb-source anythingllm`，后者优先（强制使用 AnythingLLM）。

**7 模块分析框架**:
- M1: 项目概况与投标建议
- M2: 技术要求分析矩阵（支持 AnythingLLM 查询产品能力）
- M3: 商务要求与合同条款
- M4: 评分细则与得分策略
- M5: 废标条款与风险排序
- M6: 格式要求 Checklist
- M7: 标书撰写指导

---

### 角色 4: 撰写者 (taw) — 章节内容撰写 ✅ v3.0

**服务对象**: 乙方（投标方）
**核心任务**: 基于大纲和知识库撰写各章节内容

**核心能力提升**：
- ✅ **v3.0 Local-KnowledgeBase 全 Markdown 知识库**（2026-04-03）：图文共生模式（图片随 Markdown 段落按需加载），轻量 `kb_catalog.yaml` 目录索引替代旧版 `images.yaml` 评分匹配
- ✅ **v1.9.1 Gemini 生图回归 + 模型注册表**（2026-04-02）：三供应商（火山方舟/阿里云/Gemini），模型 ID 可配置，`/twc models` 查询可用模型
- ✅ **v1.8.0 并行写作架构**（2026-04-01）：长章节自动启用并行写作（Phase 2A 蓝图 → 2B 并发子 agent → 2C 整合审校），速度提升 3-5 倍
- ✅ **v1.7.0 draw.io 集成**（2026-03-16）：支持 draw.io 生成专业图表（架构图/流程图/组织图），导出 PNG/SVG/PDF（嵌入 XML 可编辑）
- ✅ **v1.6.1 MCP 搜索工具优化**（2026-03-09）：多工具检测（Tavily/Exa），顺序降级链，精细化控制（`--search-tool tavily/exa`）
- ✅ **v1.6.0 图片生成简化**（2026-03-09）：显式参数控制，删除复杂降级逻辑，失败透明化
- ✅ **v1.4.0 AI 图片生成**（2026-03-08）：支持火山方舟 Seedream 5.0 Lite + 阿里云通义万相，2K 分辨率
- ✅ **v1.3.0 MCP 搜索工具集成**（2026-03-07）：支持 Tavily Search、Exa Search，字数提升至 4,500+ 字

**使用**:
```bash
# 目录简写（自动匹配最新大纲和分析报告）
/taw <目录> --chapter <章节编号>

# 显式指定文件
/taw --outline <大纲.docx|目录> --report <分析报告.md|目录> --chapter <章节编号>

# 指定厂商身份
/taw <目录> --chapter <章节编号> --vendor "博云"

# 搜索工具控制
/taw <目录> --chapter <章节编号> --search-tool tavily  # Tavily Search
/taw <目录> --chapter <章节编号> --search-tool exa     # Exa Search
/taw <目录> --chapter <章节编号> --search-tool mcp     # 任意可用 MCP 工具
/taw <目录> --chapter <章节编号> --search-tool websearch  # WebSearch
/taw <目录> --chapter <章节编号> --search-tool auto    # 自动选择（默认）

# 图片来源控制
/taw <目录> --chapter <章节编号> --image-source auto        # 自动选择（默认，按 H3 上下文独立选择最合适来源）
/taw <目录> --chapter <章节编号> --image-source local       # 本地知识库图片
/taw <目录> --chapter <章节编号> --image-source drawio      # draw.io 生成图表
/taw <目录> --chapter <章节编号> --image-source ai          # AI 生成图片（火山方舟/阿里云/Gemini）
/taw <目录> --chapter <章节编号> --image-source web         # 互联网下载图片
/taw <目录> --chapter <章节编号> --image-source placeholder # 占位符

# 自定义搜索词
/taw <目录> --chapter <章节编号> --query "ACP 容器云 多集群"

# 构建知识库索引
/taw --build-kb-index
```

**主要参数**:
| 参数 | 说明 |
|------|------|
| `--outline` | taa 生成的投标文件大纲（DOCX）或所在目录 |
| `--report` | taa 生成的招标分析报告（Markdown）或所在目录 |
| `--chapter` | 目标章节，支持：`5.3`（单节）、`五`/`5`（整章）、`5.1-7.2`（范围）、`all`（全部） |
| `--vendor` | 厂商名称，默认"灵雀云"，影响角色定义、搜索词、写作视角 |
| `--query` | 自定义搜索词，覆盖默认模板 |
| `--search-tool` | 搜索工具：`auto`（默认）、`websearch`、`mcp`、`tavily`、`exa` |
| `--image-source` | 图片来源：`auto`（默认，按 H3 上下文独立选择）、`local`（本地知识库图片）、`drawio`、`ai`、`web`、`placeholder` |
| `--image-provider` | AI 生图供应商：`ark`/`dashscope`/`gemini`（覆盖 `default_provider` 配置） |
| `--anythingllm-workspace` | 指定 AnythingLLM workspace slug |

**输出**:
```
drafts/
└── <章节号>_<章节名>.docx    # 单节生成
└── <起始节>-<结束节>_合并.docx  # 批量生成
```

**执行流程**:
Phase 0 输入与配置检测 → Phase 1 撰写准备（知识库检索 + 图片获取）→ Phase 2 内容生成 → Phase 3 质量自检与输出

---

## 统一配置管理 (twc)

所有 skill 共享统一配置文件 `~/.config/tender-workflow/config.yaml`，通过 `/twc` 命令管理。

```bash
# 交互式首次配置（6 步引导：知识库路径 → AnythingLLM → draw.io → AI 生图 API → Skill 默认值 → 验证）
/twc setup

# 查看当前配置
/twc show              # 全部配置
/twc show taw          # 仅 taw 视角（含全局 + taw 专属）

# 设置配置项（支持 dot notation）
/twc set localkb.path /data/kb
/twc set taa.vendor "博云"
/twc set tpl.default_template government

# 查看可用的 AI 生图模型（三供应商：火山方舟/阿里云/Gemini）
/twc models              # 全部模型
/twc models gemini       # 仅 Gemini 模型

# 健康检查（路径、API 连通性、工具安装）
/twc validate

# 从旧 per-skill 配置迁移（~/.config/taw/ 和 ~/.config/taa/）
/twc migrate
```

**配置解析优先级**：CLI 参数 > 环境变量 > 统一配置(skill 节) > 统一配置(全局节) > 默认值

**配置工具**：`skills/twc/tools/tw_config.py`（支持 CLI 调用和 Python import 两种方式）

---

## 开发指南

### 环境初始化

clone 后执行一次，激活 pre-commit hook：

```bash
git config core.hooksPath tools/hooks
```

### Pre-commit Hook

当提交包含 `SKILL.md` 或 `prompts/` 变更时，自动运行 `tests/test_skill_refs.py`，检查：

- SKILL.md 中引用的文件路径是否存在
- SKILL.md 中引用的 YAML key 是否存在

手动运行：`python3 -m pytest tests/test_skill_refs.py -v`
