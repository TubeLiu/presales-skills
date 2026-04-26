# TAW — 投标文件撰稿助手 技术文档

> 版本：v3.0.0 | 角色：撰稿者 (Tender Article Writer) | 服务对象：乙方（投标方）

---

## 1. 设计目标

TAW 是四角色系统中最复杂的 Skill，负责根据 TAA 产出的分析报告和大纲，结合多来源知识库和互联网检索，生成高质量的投标文件章节内容草稿。

核心设计原则：
- **评分导向**：所有内容围绕 M4 评分标准组织，确保每个评分点有实质性响应
- **图文共生**：知识库采用 Markdown + 内嵌图片引用格式，AI 阅读文本时自然感知图文关系，无需独立的图片匹配算法
- **多源融合**：Local-KnowledgeBase（推荐）/ AnythingLLM / 本地 YAML + 互联网检索并行，取最优结果
- **按需并行**：长章节自动路由到并行写作模式，短章节走顺序模式

---

## 2. 章节层级与字数体系

TAW 的撰写粒度以**大纲子节**为基本单元，支持最深五级标题：

| 层级 | 格式示例 | Heading Level | 默认字数 | 可覆盖参数 |
|------|---------|--------------|---------|-----------|
| 二级（H2） | 1.3 总体方案设计 | Heading 2 | 由模板定义（如 4500） | `--l2-words` |
| 三级（H3） | 1.3.1 技术架构设计 | Heading 3 | 900 字 | `--l3-words` |
| 四级（H4） | 1.3.1.1 应用层架构 | Heading 4 | 600 字 | `--l4-words` |
| 五级（H5） | 1.3.1.1.1 微服务框架 | Heading 5 | 400 字 | `--l5-words` |

**重要原则**：生成内容的标题结构**严格遵循大纲的子节结构**。若大纲定义了子节标题，则必须使用这些标题，不可自创。

---

## 3. 知识库架构（v3.0 重大变更）

### 3.1 Local-KnowledgeBase 格式（推荐）

v3.0 引入全 Markdown 知识库格式，每个知识单元为一个目录：

```
Local-KnowledgeBase/
├── 技术方案-容器云平台/
│   ├── *.md                 # 主文档（.md，索引器自动发现）
│   └── images/              # 文档引用的图片（可选）
│       ├── arch-overview.png
│       └── deploy-flow.png
├── 交付方案-实施方法论/
│   ├── *.md
│   └── images/
└── .index/
    └── kb_catalog.yaml      # 目录索引（kb_indexer.py 自动生成）
```

**图文共生原理**：主文档中通过标准 Markdown 语法引用图片（如 `![架构总览](images/arch-overview.png)`）。AI 阅读 Markdown 段落时，自然看到文字与图片引用的共存关系——无需额外的正则匹配规则或评分公式来判断"哪张图片属于哪个 H3"。图片就在文本旁边，关系不言自明。

**目录索引**（`kb_catalog.yaml`）仅做路由用途，每条包含：

| 字段 | 说明 |
|------|------|
| dir | 目录名 |
| file | 实际发现的主文档文件名 |
| title | 从主文档首个标题提取 |
| category | 从目录名前缀推断（technical/delivery/other） |
| headings | 前 5 个 H2 标题（用于消歧） |
| summary | 正文前 100 字（用于消歧） |

### 3.2 配置

```yaml
# ~/.config/tender-workflow/config.yaml
localkb:
  path: /path/to/Local-KnowledgeBase   # KB 根目录
```

---

## 4. 撰写上下文获取机制

TAW 从 TAA 产出物中获取以下撰写上下文：

### 4.1 从招标分析报告（.md）中提取

| 模块 | 匹配模式 | 用途 |
|------|---------|------|
| M2 | `## M2` 或 `## 二、技术要求` | 技术要求矩阵 → 内容生成的需求基础 |
| M4 | `## M4` 或 `## 四、评分标准` | 评分细则 → 决定内容深度和展开重点 |
| M5 | `## M5` 或 `## 五、废标条款` | 红线条款 → 内容生成的负面约束 |
| M7 | `## M7` 或 `## 七、投标策略` | 撰写指导 → 优先级/关键词/亮点/红线 |

**定位方式**：每个模块从 `##` 标题行开始，到下一个同级标题行结束。使用 Grep 搜索标题快速定位行号，再用 Read 读取区间内容。

### 4.2 从投标文件大纲（.docx）中提取

使用 python-docx 提取文本，识别 Heading 样式获取标题层级：

1. **章节编号与标题**：构建大纲目录树
2. **目标章节内容**：定位用户指定章节号对应的段落
3. **子节标题列表**：提取所有层级子节（最深至第5级），记录 `{numbering, title, depth}`

---

## 5. 工作流程（4 Phase）

### Phase 0：输入文件加载与验证

```
Step 0: 帮助参数检测
Step 1: 输出目录初始化
Step 1.5: 搜索工具检测（tavily_search / exa_search / WebSearch）
Step 1.6: AnythingLLM 可用性检测 + workspace 确定
Step 1.7: draw.io 可用性检测（Skill + CLI 双重检测）
Step 2: --set-kb 处理（永久保存知识库路径）
Step 2b: --build-kb-index 处理（扫描 Local-KnowledgeBase 目录，生成 kb_catalog.yaml 索引并退出）
Step 3: 文件路径解析（支持显式参数/目录简写两种模式）
Step 4: KB 路径解析 + 厂商/搜索工具/图片来源/字数配额参数解析
Step 5: --chapter 解析 → CHAPTERS_TO_WRITE 列表
```

**章节解析支持多种格式**：
- `一`（整章 11 节）
- `1.3`（单节）
- `all`（全部）
- `1.1-1.9` / `1.1到1.9` / `1.1至1.9`（范围）

### Phase 1：撰写准备

#### 1.1 章节模板加载与评分映射

```
Step 1: 读取核心模板 article_core.yaml + 章节类型匹配器 chapter_type_matcher.yaml
Step 2: 从大纲提取目标章节标题 + 子节标题列表（OUTLINE_SUBSECTIONS）
Step 3: 章节类型语义匹配（关键词匹配 + LLM 语义理解）
        → business / technical / service / commitment
Step 4: 加载对应章节模板 article_templates/{type}.yaml
        → 提取 word_count、content_elements、kb_priority、image_types
        → 读取 image_guidelines.yaml 获取图片护栏配置
```

**章节类型匹配原理**：
1. 提取章节标题关键词（去除编号）
2. 与 `chapter_type_matcher.yaml` 各类型的 keywords 语义匹配
3. 计算匹配度（关键词交集 / 总关键词数）
4. 匹配度 < 0.6 时降级到 LLM 语义理解
5. 返回类型 + 置信度

**评分映射提取**：从 M4 中筛选与目标章节相关的评分项，标注高分值项（>=10 分）为重点展开项。

#### 1.2 M7 撰写指导提取

从 M7 提取与目标章节直接相关的：
- 撰写优先级（P1/P2/P3）
- 关键词清单
- 写作策略
- 差异化亮点
- 红线约束

#### 1.3 知识库检索（强制步骤）

**知识库来源策略**（由 `--kb-source` 参数控制）：

| 参数值 | AnythingLLM | 本地知识库 | 互联网检索 |
|--------|-------------|-----------|-----------|
| `auto`（默认） | 并行查询 | 并行查询 | 并行执行 |
| `anythingllm` | 强制使用 | 跳过 | 并行执行 |
| `local` | 跳过 | 强制使用 | 并行执行 |
| `none` | 跳过 | 跳过 | 仅互联网 |

**知识库检索架构（v3.0）**：

```
优先层: Local-KnowledgeBase Markdown 检索（图文一体化）
    └── 读取 kb_catalog.yaml → 按章节主题匹配相关 KB 目录
    └── 读取主文档（matched_entry.file）相关段落 → 同时获取文字素材和内嵌图片引用
    └── 图片引用随文本段落一起记录，不做独立匹配
    └── 有效结果 >= 2 → 跳过 AnythingLLM 和 YAML 层

并行层: AnythingLLM 语义检索（KB 检索不足或不可用时）
    └── 查询: 章节标题 + M7 关键词（前5个）
    └── 过滤: score >= 0.7，最多 5 条
    └── 按来源分类标注: fixed / reusable / history

降级层: 本地 YAML 索引（上两层均不可用或结果不足时）
    ├── 第一层 fixed: 售后/维保固定条款 → 原文照搬
    ├── 第二层 reusable: 可复用方案 → 微调复用
    └── 第三层 history: 历史标书 → 按 key_sections 精准读取 + 脱敏改写

第四层: 互联网检索（与知识库并行执行）
    ├── 场景化工具选择:
    │   ├── 产品查询 → history > WebSearch > MCP
    │   ├── 技术方案 → WebSearch > MCP
    │   ├── 案例数据 → history > WebSearch > MCP
    │   └── 行业趋势 → WebSearch > MCP
    └── 搜索工具降级链:
        WebSearch → tavily_search → exa_search → [待补充]
```

**Local-KnowledgeBase 检索流程**（v3.0 新增）：

1. 读取 `kb_catalog.yaml` 目录索引
2. 按 H3 子节标题 + M7 关键词与索引条目的 title/headings/summary 语义匹配
3. 选取 top-N 相关 KB 目录（N <= 3）
4. 读取对应主文档（索引条目的 `file` 字段），定位与 H3 主题相关的段落区间
5. 段落中的 `![](images/...)` 引用自动随文本一起记录到检索结果——这就是"图文共生"

**WEB_FACTS 事实提取表**：

从搜索结果中提取结构化事实，记录为：

| 字段 | 说明 |
|------|------|
| fact_id | F001, F002, ... |
| type | 产品能力 / 技术参数 / 案例数据 / 架构描述 |
| content | 结构化事实内容 |
| source | 来源 URL 或知识库 |
| search_tool | websearch / tavily / exa |
| confidence | 高/中/低 |
| needs_verification | true/false |

**内容融合策略**（6 段结构）：

| 段落 | 字数 | 主要来源 |
|------|------|---------|
| 1. 需求理解 | 300-450 | M2 技术要求 |
| 2. 行业背景 | 450-600 | 互联网资料 |
| 3. 方案设计 | 900-1500 | KB Markdown / reusable + 互联网 |
| 4. 技术实现 | 900-1500 | 互联网 + KB history |
| 5. 案例佐证 | 450-600 | KB history |
| 6. 预期效果 | 300-450 | M4 评分标准 |

#### 1.4 准备确认

**必须包含知识库来源统计**：
- Local-KnowledgeBase 匹配目录数 + 段落数
- AnythingLLM 结果数
- 本地 YAML 各层结果数
- 互联网检索结果数
- 图片护栏配置信息

---

### Phase 2：内容生成

#### 写作模式路由

每个章节根据以下条件决定写作模式：

```python
USE_PARALLEL_WRITING = (H3_COUNT >= 3) and (TARGET_WORDS >= 4500)
```

- **True** → 并行写作模式（Phase 2A → 2B → 2C）
- **False** → 顺序写作模式（Step 2a-2d）

#### 并行写作模式（三阶段）

##### Phase 2A：写作蓝图生成

读取 `prompts/writing_brief_template.yaml`，生成结构化 Writing Brief：

**蓝图组件**：

1. **论述主线**（<=200 字）：全章核心论证逻辑，体现"问题→方案→价值"递进

2. **H3 分工表**（核心）：

| 字段 | 说明 |
|------|------|
| h3_numbering | 子节编号 |
| h3_title | 子节标题 |
| core_argument | 核心论点（1 句话） |
| scoring_points | 需覆盖的 M4 评分项 ID |
| kb_materials | 应引用的 KB 条目 |
| web_facts | 应引用的 WEB_FACTS ID |
| target_words | 目标字数（按评分权重分配） |
| connect_from | 承接上一节的内容 |
| lead_to | 为下一节铺垫的内容 |

**字数分配规则**：
- 可分配字数 = TARGET_WORDS - 500（预留引言 300 + 总结 200）
- 按 M4 评分项分值加权：高分项 x1.5 / 中分项 x1.0 / 低分项 x0.7
- 每个 H3 最少 `--l3-words` 或 900 字

3. **术语表**（<=20 条）：统一用语 / 禁用变体 / 使用场景

##### Phase 2B：并发子智能体撰写

1. 读取 `prompts/parallel_writer_agent.yaml` 获取子智能体提示模板
2. 为每个 H3 打包上下文（论述主线 + 术语表 + H3 任务 + M4 评分项 + KB 素材 + WEB_FACTS）
3. **在单条消息中同时分发所有子 Agent**，确保并发执行
4. 收集结果并检查（字数/术语/跑题/超时）
5. **>50% 子 agent 失败 → 降级到顺序写作模式**

**每个子 Agent 上下文约 2600 tokens**，不传递完整分析报告和其他 H3 的数据。

##### Phase 2C：整合审校

1. 按 H3 顺序拼接所有子 Agent 输出
2. 生成章节引言段（200-300 字）
3. 检查并补充相邻 H3 间的过渡段落
4. **一致性审校**：术语扫描 + 矛盾检测 + 重复消除
5. **M4 评分覆盖终检**：逐一确认每个评分项有实质性响应
6. 生成章节结尾段（100-200 字）
7. → 继续执行图片获取 → 大纲对齐自检 → Phase 2.5 → Phase 3

#### 顺序写作模式

当 `USE_PARALLEL_WRITING=false` 时（H3 < 3 或字数 < 4500），按以下步骤顺序生成：

```
Step 2a: 每节写作前 — 检查 WEB_FACTS，执行定向搜索（<=2次）
Step 2b: 图片获取 — AI 驱动的三情境图片处理
Step 2c: 长内容分段生成 — 目标字数 >= 4500 且无大纲子节时触发
         拆分为 3-5 个子主题，每个 900-1500 字
Step 2d: 大纲子节标题对齐 — 生成内容标题必须严格遵循大纲结构
```

**Step 2c 分段生成触发条件**：
- 章节目标字数 >= 4500 字
- 且 OUTLINE_SUBSECTIONS 为空（大纲无子节）
- 若大纲有子节 → 直接以子节作为分段依据，不触发此机制

#### 图片处理策略（v3.0 重大变更）

v3.0 用 **AI 驱动的三情境判断**替代了 v2.0 的正则规则 + 评分公式。AI 读取 `image_guidelines.yaml` 的护栏配置，对每个 H3 子节判断属于以下哪种情境：

##### 情境 A：KB 图文共生（最常见）

**触发条件**：Phase 1.3 的 Local-KnowledgeBase 检索已在该 H3 的相关段落中发现内嵌图片引用。

**处理方式**：
1. AI 确认图片与当前写作上下文仍相关
2. 生成动态 caption：结合 H3 标题 + 图片在 KB 中的上下文
3. 直接记录到 SECTION_IMAGES，来源标记为 `kb-colocated`

**核心优势**：不需要独立的图片匹配算法——图片引用与文字段落天然共存于同一个 Markdown 主文档中，AI 阅读文本时自然感知图文关系。

##### 情境 B：AnythingLLM + KB 分离获取

**触发条件**：`--kb-source anythingllm`（文字来自 AnythingLLM，图片通过 `auto` 模式的 KB 图文共生机制从本地 KB 目录自动获取）。

**处理方式**：
1. AI 用 H3 主题查 `kb_catalog.yaml` → 选相关 KB 文档
2. Grep 主文档标题 → 定位与 H3 主题相关的段落
3. Read 段落 → 从中提取 `![](images/...)` 引用
4. AI 判断图片与 H3 内容的相关性 → 记录到 SECTION_IMAGES

##### 情境 C：AI 自主决策（无 KB 匹配时的兜底）

**触发条件**：该 H3 无 KB 图片匹配，由 `--image-source` 参数决定获取方式。

| 模式 | 尝试顺序 | 失败处理 |
|------|---------|---------|
| `auto` | draw.io → AI 生图 → placeholder | 逐级降级 |
| `drawio` | draw.io Skill/CLI | 占位符 |
| `ai` | 通过 `Skill(skill="ai-image:gen")` 调用 ai-image plugin（使用其配置的默认供应商） | 占位符 |
| `web` | WebSearch + curl 下载 | 占位符 |
| `placeholder` | 直接生成占位符 | — |

AI 参考 `image_guidelines.yaml` 中的 `no_kb_hints` 判断该 H3 是否真正需要图片（例如"纯文字论述"类 H3 可跳过）。

**图片护栏**（`image_guidelines.yaml`，硬限制不可覆盖）：

| 护栏 | 值 | 说明 |
|------|------|------|
| chapter_max | 8 | 单章节最大图片数 |
| h3_max | 1 | 单个 H3 最多 1 张图片 |
| chapter_dedup | true | 同章节不重复使用同一图片 |
| cross_chapter_dedup | true | 跨章节不重复（GLOBAL_USED_IMAGES） |
| min_file_size_kb | 5 | 低于 5KB 的图片跳过 |

**与 v2.0 的对比**：

| 维度 | v2.0 | v3.0 |
|------|------|------|
| 图片需求判断 | 14 条正则规则匹配 H3 标题关键词 | AI 阅读 H3 内容 + KB 上下文自主判断 |
| 图片匹配打分 | 5 维度加权评分（type_match 40 + keyword 30 + layer 15 + quality 10 - dedup 50） | 图文共生——图片与文字在同一个 Markdown 文件中共存，无需独立打分 |
| 配额管理 | `chapter_image_quota.yaml` 静态配额表 | `image_guidelines.yaml` 护栏上限 + AI 自主决策 |
| H3 分配 | `h3_allocation_rules` 正则 → 固定配额 | 无固定配额，AI 按内容语义决定 |

### Phase 2.5：执行阶段自检

每节内容生成完成后、写入 DOCX 前强制执行：

| 自检项 | 检查内容 |
|--------|---------|
| 2.5.1 内容格式 | Markdown 标记是否通过 write_markdown() 写入 |
| 2.5.2 图片获取 | SECTION_IMAGES 是否记录，数量是否在护栏范围内 |
| 2.5.3 大纲对齐 | 子标题与大纲子节一一对应，层级与 depth 一致 |
| 2.5.4 知识库使用 | 至少一种知识库来源有命中 |
| 2.5.5 并行写作一致性 | 术语一致/无重复/过渡质量/评分覆盖（仅并行模式） |

### Phase 3：质量自检与输出

#### 3.1 质量自检

| 自检项 | 通过标准 |
|--------|---------|
| 评分覆盖度 | M4 相关评分点 100% 有响应 |
| 关键词覆盖率 | M7 关键词 >= 80% |
| 废标红线 | M5 + M7.5 零违反 |
| 过度承诺 | 零绝对化措辞 |
| 待确认标注 | 无 KB 支撑的内容全部标注 |
| 图片护栏合规 | 单章 <= 8 张，单 H3 <= 1 张，无重复 |

#### 3.2 DOCX 生成

**关键技术点**：

1. **write_markdown() 函数**：所有正文内容的唯一写入入口，解析 **粗体** / *斜体* / `代码` / 列表 / 表格
2. **禁止 add_para_cn()**：该函数不解析 Markdown 标记，会导致 `**文本**` 原样输出到文档
3. **字体规范**：中文宋体 + 英文 Times New Roman，通过 `setup_styles()` + `clean_doc_defaults()` + `apply_run_font()` 三层设置确保跨平台一致
4. **字符串用单引号**：Python 代码中所有字符串参数用 `'...'`，避免中文引号触发 SyntaxError

**输出文件**：
- 单节模式：`drafts/<章节号>_<章节名>.docx`
- 多节模式：`drafts/<起始节>-<结束节>_合并.docx`

---

## 6. 多节模式优化

当 CHAPTERS_TO_WRITE 含多个章节时：

### 全局知识池（GLOBAL_KNOWLEDGE_POOL）

Phase 1.3 开始时执行 <= 2 次全局搜索，提取通用知识：
- vendor_info（产品列表/核心能力/典型案例/资质认证）
- industry_trends（行业趋势）
- technical_standards（技术标准）

每节写作时优先从池中提取，不足时再做 <= 2 次定向搜索，新知识回补到池中。

### 多节合并输出

所有章节合并为单个 DOCX，章节间用分节符分隔，每节完成后输出进度提示：
```
[进度 3/11] 1.3 总体方案设计 -- 4,500字，插图 2/2 张（实插 1 / 占位符 1）
```

---

## 7. Prompt 文件与工具架构

```
skills/taw/
├── SKILL.md                              # 主编排 Prompt
├── prompts/
│   ├── article_core.yaml                 # 全局规则、角色定义、输出格式
│   ├── article_templates/                # 章节模板（按类型语义匹配）
│   │   ├── business.yaml                 # 商务部分
│   │   ├── technical.yaml                # 技术部分
│   │   ├── service.yaml                  # 服务部分
│   │   └── commitment.yaml               # 承诺部分
│   ├── chapter_type_matcher.yaml         # 章节类型语义匹配器
│   ├── chapter_image_quota.yaml          # 图片配额策略（v2.0 遗留，deprecated）
│   ├── image_guidelines.yaml             # 图片处理护栏（v3.0 新增，替代配额策略）
│   ├── ai_image_models.yaml              # AI 生图模型注册表
│   ├── writing_brief_template.yaml       # 并行写作蓝图格式规范
│   └── parallel_writer_agent.yaml        # 并行写作子智能体提示模板
└── tools/
    ├── docx_writer.py                    # DOCX 输出
    └── kb_indexer.py                      # Local-KnowledgeBase 目录索引生成器
# AI 生图通过 ai-image plugin（slash /ai-image:gen 或自然语言）
# draw.io 图表通过 drawio plugin（slash /drawio:draw 或自然语言）
```

---

## 8. 新增命令参数（v3.0）

```bash
# 生成 Local-KnowledgeBase 目录索引
/taw --build-kb-index
/taw --build-kb-index --kb-path /path/to/Local-KnowledgeBase

# 等价的直接调用
python skills/taw/tools/kb_indexer.py --scan
python skills/taw/tools/kb_indexer.py --scan --kb-path /path/to/KB --output /path/to/output.yaml
```

---

## 9. 与其他 Skill 的关系

```
[TAA] 招标分析报告.md ──→ TAW 读取 M2/M4/M5/M7
[TAA] 投标文件大纲.docx ──→ TAW 读取章节结构和子节标题
[TWC] config.yaml ──→ TAW 读取 localkb.path / anythingllm / ai_image 等配置
[TAW] 章节草稿.docx ──→ [TRV] 审核（chapter 类型）
[TAW] 全部章节合并 ──→ [TRV] 审核（full_bid 类型）
```

TAW 与 TAA **完全解耦**——不直接调用 TAA 的代码，仅通过读取 TAA 的 Markdown/DOCX 产出物获取信息。

---

## 10. 向后兼容性（v3.0）

| 维度 | 说明 |
|------|------|
| `chapter_image_quota.yaml` | deprecated，v3.0 使用 `image_guidelines.yaml` |
| `--image-source` 参数 | 所有选项（auto/local/drawio/ai/web/placeholder）不变 |
| `--l2-images` / `--l3-images` | 仍生效，但在 v3.0 中优先级低于护栏上限 |
| 并行写作 | 不受影响，Phase 2A/2B/2C 流程不变 |
| draw.io 集成 | 不受影响 |
| AI 图片生成 | 不受影响，使用 `default_provider` 指定供应商（失败时报错并使用占位符） |
| `--build-index` | 已废弃，改用 `--build-kb-index` |
| `--build-kb-index` | v3.0 新增，扫描 Local-KnowledgeBase 目录，生成 kb_catalog.yaml 索引并退出 |
