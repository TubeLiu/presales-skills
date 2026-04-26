# taw 知识库 + 互联网检索详细规则

主 SKILL.md §Phase 1.3 列了"KB 检索强制 + 与 Web 并行"的高层约束；本文件给四层检索的具体执行步骤。

## 0. 核心原则

- 所有匹配基于**内容主题/关键词语义**，与章节号无关
- `--kb-source local` → 强制本地 KB 目录索引，跳过 AnythingLLM
- `--kb-source none` → 跳过所有 KB（文字 + 图片均走 WebSearch）
- KB `reusable` 既有文字又有图 → 直接用，不走其他图片逻辑

## 1. 全局知识池（多节模式优化）

触发：`CHAPTERS_TO_WRITE ≥ 2 个章节` 且 `NO_KB_FLAG=false`。

`GLOBAL_KNOWLEDGE_POOL`：

```yaml
vendor_info:
  products: []           # 产品（名称/版本/核心能力）
  capabilities: []       # 核心能力（技术特性/性能指标）
  cases: []              # 典型案例（客户类型/项目规模/实施时间）
  certifications: []     # 资质认证（ISO/信创/安全等级）
industry_trends: []      # 行业趋势
technical_standards: []  # 技术标准（K8s/CNCF/国标）
```

填充策略（Phase 1.3 开始执行）：

1. 全局搜索 ≤ 2 次 WebSearch（不计入后续每节配额）：
   - `"{VENDOR_NAME} 产品线 核心能力 2026"`
   - `"{项目行业} 技术趋势 最佳实践 2026"`
2. 结构化提取产品/趋势/标准
3. 后续每节优先从池中提取，不足时再 ≤ 2 次定向搜索补充池

单节模式跳过全局池，直接定向搜索。

## 2. 当前章节语义上下文

```
章节语义上下文 = 章节标题 + 章节内容纲要 + M7 关键词（取前 10 个最相关）
```

## 3. 文字检索（KB + 互联网并行，强制执行）

### 优先层 A：Local-KnowledgeBase Markdown（图文一体化）

触发：`{KB_ROOT}/.index/kb_catalog.yaml` 存在 且 `NO_KB_FLAG=false`。

核心：从 Markdown 文档同时获取文字 + 图片引用。

执行：

1. Read `{KB_ROOT}/.index/kb_catalog.yaml`，获取 `entries` 列表（每条含 dir/title/category/headings/summary）
2. AI 选与当前章节相关的 KB 文档（1-5 个）：
   - 匹配依据：章节标题 + M2 技术要求关键词 ↔ 索引的 title/headings/summary
   - 多版本消歧：目录名含版本号时优先最新版
   - 分类过滤：技术章节优先 `category=technical`
   - **宁多勿漏**：实质关联即纳入候选，段落级再筛
3. 多文档互补分工（≥ 2 个文档时）：
   - 按 H3 子节分配：每个 H3 优先从 1-2 个最贴合的文档取材
   - 互补：不同文档提供不同维度（A 架构 / B 实施 / C 运维）
   - 禁止重复拼接；若覆盖相同主题取最详实的一个
4. 段落选取：
   ```
   main_md_file = matched_entry.get("file", "full.md")
   full_md_path = KB_ROOT / matched_entry.dir / main_md_file
   Grep ^# 取标题列表 → AI 选最相关 → Read 行范围
   ```
5. 在读取段落中获得：
   - **文字** → 记录 `KB_MATERIALS`（标注来源 dir）
   - **图片引用** `![](images/HASH.jpg)` → AI 判断与 H3 相关性，相关则记录 `MATCHED_IMAGES`：`{h3_numbering, image_path: KB_ROOT/dir/images/HASH.jpg, context: 图片前后文字}`
6. 有效结果数 ≥ 2 → 跳过下方 AnythingLLM 层；否则降级

注意：此层与互联网检索**并行**（不互斥）。

### 优先层 B：AnythingLLM 语义检索

触发：`ANYTHINGLLM_AVAILABLE=true` 且 `NO_KB_FLAG=false`。

执行：

1. 查询：`章节标题 + M7 关键词（取前 5 个）`
2. `anythingllm_search(query=..., workspace=ANYTHINGLLM_WORKSPACE)`
3. 过滤 `score >= 0.7`（最多 5 条）
4. 来源标注：
   - `metadata.chunkSource` 含 `fixed` → `[来源：固定条款，不可修改]`
   - 含 `reusable` → `[来源：可复用方案，微调使用]`
   - 含 `history` → `[来源：历史案例，改写提炼，注意脱敏]`
   - 其他 → `[来源：知识库，参考使用]`
5. 有效结果数 ≥ 2 → 进入互联网层；否则仅依赖互联网兜底

### 第四层：互联网检索（并行执行，场景化工具选择）

触发：与 KB 检索同时（不等前层失败）。

#### 厂商优先站点

```
Read $SKILL_DIR/prompts/vendor_sites.yaml
```

- 用 `VENDOR_NAME` 匹配 `vendors[].vendor_name` 或 `aliases`（不区分大小写）
- 匹配到 → `VENDOR_SITES = sites 列表`
- 未匹配 → `VENDOR_SITES=[]`
- 加载 `authority_sites`（通用权威站点）

#### 搜索执行策略

每个搜索场景：先用 `VENDOR_SITES + authority_sites` 定向（`allowed_domains`），再不限域名补充。定向结果优先纳入 `WEB_FACTS`。

#### 工具选择（按 SEARCH_TOOL_OVERRIDE）

- `tavily` → `["tavily_search"]`
- `exa` → `["exa_search"]`
- `mcp` → `MCP_TOOLS_AVAILABLE`（按 priority）
- `websearch` → `["WebSearch"]`
- `auto`（默认）→ `["WebSearch"] + MCP_TOOLS_AVAILABLE`

按顺序尝试每个工具：

#### 1) WebSearch

定向（VENDOR_SITES 非空）：
```
WebSearch(query="{VENDOR_NAME} {章节主题} {场景关键词}", allowed_domains=VENDOR_SITES)
```

补充（不限域）按场景：

| 场景 | 触发词 | 查询 |
|---|---|---|
| A 产品能力 | 产品名/版本/功能/参数 | `{VENDOR_NAME} {产品} {功能}` |
| B 技术方案/架构 | 架构/设计/最佳实践 | `{项目行业} {章节主题} 技术方案 最佳实践` |
| C 案例数据 | 案例/客户/项目 | `{VENDOR_NAME} {章节主题} 案例 项目` |
| D 行业趋势/标准 | 趋势/标准/演进 | `{项目行业} {章节主题} 趋势 标准`（`allowed_domains=authority_sites.standards+technical`） |

#### 2) tavily_search

```
tavily_search(query="{项目行业} {章节主题} 技术方案", search_depth="advanced", max_results=5)
```

超时 30s；失败尝试下一工具。

#### 3) exa_search

```
exa_search(query="{项目行业} {章节主题} 技术方案", num_results=5, use_autoprompt=True)
```

超时 30s；失败尝试下一工具。

#### 降级链 + 强制工具

- 当前工具超时 / 错误 → 下一工具
- 所有失败 → 标注 `[待补充]`

强制指定时：
- `tavily` / `exa` → 失败报错不降级
- `mcp` → 全部失败报错
- `websearch` → 失败标注 `[待补充]`

## 4. 查询词构建

- 主：`"{项目行业} {章节主题关键词} 解决方案 最佳实践"`
- 补充：`EXTRA_QUERY` 非空时用之；否则 `"{VENDOR_NAME} {M7 核心关键词} 案例"`

## 5. 搜索次数限制

- `NO_KB_FLAG=true`：≤ 4 次 / 章节
- 否则：≤ 3 次 / 章节（定向 1 + 补充 1 + MCP 1，共享配额）

## 6. 结果处理 + 事实提取

- 格式适配：Read `$SKILL_DIR/prompts/fact_extraction_rules.yaml` 中 `search_result_formats`～`unified_extraction_flow`
- 事实提取：Read 同文件 `web_facts_schema`～`multi_chapter_mode`，提炼结构化 `WEB_FACTS` 表

## 7. 标注规则

| 来源 | 标注 |
|---|---|
| Tavily 数字/指标 | `[Tavily来源，请核实]` |
| Exa 数字/指标 | `[Exa来源，请核实]` |
| WebSearch 数字/指标 | `[互联网来源，请核实]` |
| 知识库 | `[知识库来源]` |
| 通用技术描述 | 不必逐句标注 |

不得照搬原文；结合 M2 / M4 / M7 针对本项目改写。

## 8. 内容融合策略（Phase 2 写作时应用）

每个 H3 引用 WEB_FACTS ≤ 5 条；同语义重叠仅留最详实（confidence 高优先）；优先凑齐不同 type 多维度论证。KB 与 Web 重叠时优先 KB，Web 作补充。详见 `fact_extraction_rules.yaml::selection_rules`。

章节内容典型分配：

1. **开篇 / 需求理解**（300-450 字）— M2 原文
2. **行业背景**（450-600 字）— Web 趋势
3. **方案设计**（900-1500 字）— KB reusable + Web 技术方案
4. **技术实现**（900-1500 字）— Web 细节 + KB 实施经验
5. **案例佐证**（450-600 字）— KB 案例
6. **预期效果**（300-450 字）— M4 评分点

## 9. KB 强制执行检查点

- KB 目录索引：必须读取 `kb_catalog.yaml`，禁止假设为空而不读
- AnythingLLM：`auto` 或 `anythingllm` 时必须实际调用，记录结果数
- Phase 1.4 输出必须含 KB 来源统计；KB 未使用必须明确原因（未配置 / 调用失败 / 文件不存在 / entries 空 / 无匹配）
- 若 KB + AnythingLLM 都"⚠️ 未使用" → 禁止进入 Phase 2，必须重跑 Phase 1.3
