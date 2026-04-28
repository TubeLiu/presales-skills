# taw — 投标文件撰稿助手

**中文** | [English](./README_EN.md)

**taw**（Tender Article Writer）是投标工作流的核心撰稿角色，基于 `taa` 产出的**招标分析报告**和**投标文件大纲**，结合公司知识库，自动生成高质量的投标文件章节草稿（DOCX 格式）。

**版本**：v3.0.0 | **最后更新**：2026-04-03

---

## 核心亮点

### 1. 图文共生模式（v3.0.0 新增）
- AI 直接读取知识库 Markdown 文件，自然感知内嵌的图片引用（`![](images/xxx.png)`）
- 无需正则匹配模式或评分公式 -- 图片随段落上下文一同加载，天然关联
- `kb_indexer.py` 生成轻量目录索引（`kb_catalog.yaml`），仅存目录/标题/分类/摘要
- `image_guidelines.yaml` 提供图片使用护栏（数量上限、尺寸规范、占位符规则）
- 无匹配知识库图片的 H3 子节自动回退到 AI 生图或占位符

### 2. 并行写作架构（v1.8.0+）
- ✅ 长章节（≥3 个 H3 子节且 ≥4,500 字）自动启用并行写作模式
- ✅ Phase 2A：写作蓝图生成（论述主线、H3 分工表、术语表、字数分配）
- ✅ Phase 2B：并发子智能体撰写（每个 H3 子节独立 agent 并行执行）
- ✅ Phase 2C：整合审校（过渡补充、术语统一、矛盾检测、评分覆盖终检）
- ✅ 智能路由：根据章节复杂度自动判断并行/顺序模式
- ✅ 优雅降级：>50% 子 agent 失败时自动降级到顺序写作模式

### 3. draw.io 专业图表生成
- ✅ 支持 draw.io 生成专业图表（架构图/流程图/组织图/序列图）
- ✅ 生成可编辑的 .drawio 源文件
- ✅ 支持导出 PNG/SVG/PDF（嵌入 XML，可在 draw.io 中再次编辑）
- ✅ 自动检测 draw.io CLI 路径（macOS/Windows/Linux）

### 4. 多 MCP 搜索工具支持
- ✅ 检测所有可用的 MCP 工具（Tavily Search、Exa Search）
- ✅ 顺序降级链：工具失败时自动降级到下一个可用工具
- ✅ 精细化控制：`--search-tool tavily/exa/mcp/websearch/auto`
- ✅ 区分标注：不同工具来源使用不同标注

### 5. 灵活的图片来源控制
- ✅ 统一参数 `--image-source` 控制：`auto`/`local`/`drawio`/`ai`/`web`/`placeholder`
- ✅ 双 API 支持：火山方舟 Seedream 5.0 Lite + 阿里云通义万相（2K 分辨率）
- ✅ 失败透明化：指定方案失败后使用占位符，不隐式降级

### 6. 深度内容生成能力
- ✅ 核心章节 4,500+ 字：分段生成机制（3-5 个子主题，每个 900-1,500 字）
- ✅ 五级标题支持：H1-H5 标题层级，适配深层大纲结构
- ✅ 字数/图片参数化：`--l2-words`/`--l3-words`/`--l2-images` 等参数覆盖默认值
- ✅ 事实提取表（WEB_FACTS）：结构化管理互联网搜索结果
- ✅ 场景化工具选择：产品查询用 WebSearch，技术方案用 MCP

### 7. 质量保证机制
- ✅ 评分覆盖度 100%（M4 评分点全部响应）
- ✅ 关键词覆盖率 ≥ 80%（M7 关键词清单）
- ✅ 废标红线零违反（M5 条款和 M7.5 红线）
- ✅ 过度承诺检测（零绝对化措辞）
- ✅ 待确认标注（无支撑内容全部标注）

---

## 目录

- [快速开始](#快速开始)
- [完整参数说明](#完整参数说明)
- [执行流程详解](#执行流程详解)
- [知识库配置](#知识库配置)
- [知识库索引构建](#知识库索引构建)
- [章节号格式详解](#章节号格式详解)
- [使用场景范例](#使用场景范例)
- [输出文件说明](#输出文件说明)
- [工作流集成](#工作流集成)
- [质量保证机制](#质量保证机制)
- [常见问题](#常见问题)

---

## 快速开始

### 前置条件

1. 已运行 `/taa` 生成招标分析报告（`output/招标分析报告_*.md`）和投标文件大纲（`output/投标文件大纲_*.docx`）
2. 已配置知识库路径（首次运行时会自动引导），或使用 `--kb-source none` 跳过

### 最简用法

```bash
# 最简：目录下自动匹配最新大纲和分析报告
/taw output/ --chapter 1.3

# 显式指定文件路径
/taw --outline output/投标文件大纲_20260305.docx --report output/招标分析报告_20260305.md --chapter 1.3

# 撰写整个技术部分（第一章全部子节）
/taw --outline output/ --report output/ --chapter 一

# 指定厂商身份（必填，可在 /twc setup 配持久值）
/taw output/ --chapter 1.3 --vendor "博云"

# 撰写所有章节（一、技术部分，共 11 节）
/taw --outline output/ --report output/ --chapter all
```

输出文件保存至 `./drafts/` 目录。

---

## 完整参数说明

```
用法：
  /taw --outline <大纲.docx|目录> --report <分析报告.md|目录> --chapter <章节号> [选项...]
  /taw <目录> --chapter <章节号>        # 简写：目录下自动匹配两个文件
  /taw --set-kb <知识库路径>
  /taw --build-kb-index
  /taw -h | --help
```

### 必选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `--outline` | 文件路径或目录 | taa 生成的投标文件大纲（DOCX 格式）或所在目录（取最新 .docx）。`--set-kb`/`--build-kb-index`/`-h` 模式下可省略 |
| `--report` | 文件路径或目录 | taa 生成的招标分析报告（Markdown 格式）或所在目录（取最新 .md）。`--set-kb`/`--build-kb-index`/`-h` 模式下可省略 |
| `--chapter <章节号>` | 章节号 | 目标章节，支持多种格式（见下方详解） |

### 可选参数

| 参数 | 说明 |
|------|------|
| `--kb <路径>` | 临时覆盖知识库路径，不修改配置文件 |
| `--kb-source <来源>` | 知识库来源控制：`auto`（默认，综合取用）、`anythingllm`、`local`、`none`（见下方说明） |
| `--set-kb <路径>` | 永久设置默认知识库路径，保存至 `~/.config/tender-workflow/config.yaml` |
| `--build-kb-index` | 扫描 Local-KnowledgeBase 目录，生成 kb_catalog.yaml 索引并退出 |
| `--image-source <来源>` | 图片来源控制：`auto`（默认，按 H3 子节上下文独立选择）、`local`（本地知识库图片）、`ai`、`web`、`drawio`、`placeholder` |
| `--search-tool <工具>` | 搜索工具控制：`auto`（默认）、`tavily`、`exa`、`mcp`、`websearch` |
| `--vendor <厂商名>` | 指定投标厂商身份（必填，可在 /twc setup 配持久值） |
| `--query <查询词>` | 手动指定补充查询词 |
| `--anythingllm-workspace <slug>` | 指定 AnythingLLM workspace slug |
| `--l2-words <字数>` | 二级章节（X.X 级）目标字数，覆盖模板默认值 |
| `--l3-words <字数>` | 三级章节（X.X.X 级）目标字数（默认 900） |
| `--l4-words <字数>` | 四级章节（X.X.X.X 级）目标字数（默认 600） |
| `--l5-words <字数>` | 五级章节（X.X.X.X.X 级）目标字数（默认 400） |
| `--l2-images <数量>` | 二级章节图片配额，覆盖模板默认值 |
| `--l3-images <数量>` | 三级章节图片配额（默认 0） |
| `-h, --help` | 显示命令帮助并退出 |

### `--kb-source` 参数详解

控制知识库来源，适用于不同场景：

| 参数值 | 说明 | 适用场景 |
|--------|------|---------|
| `auto`（默认） | 综合使用所有可用知识库，按匹配度和内容质量动态取用 | 常规使用 |
| `anythingllm` | 强制使用 AnythingLLM，不可用则报错退出 | 确保使用最新知识库 |
| `local` | 强制使用本地 YAML 索引，跳过 AnythingLLM 检测 | 无网络或 AnythingLLM 不可用 |
| `none` | 完全跳过知识库，仅依赖互联网检索 | 知识库尚未建立或需要最新资料 |

### `--kb` vs `--kb-source` vs `--set-kb`

三个参数功能不同，注意区分：

| 参数 | 作用 | 持久化 | 优先级 |
|------|------|--------|--------|
| `--kb <路径>` | 临时指定知识库路径 | ❌ 否 | 最高 |
| `--kb-source <来源>` | 指定知识库来源类型 | ❌ 否 | 中 |
| `--set-kb <路径>` | 永久设置默认知识库路径 | ✅ 是 | - |

**使用示例**：
```bash
# 临时使用指定知识库（本次运行有效）
/taw output/ --chapter 1.3 --kb /tmp/test-kb

# 强制使用 AnythingLLM（不可用则报错）
/taw output/ --chapter 1.3 --kb-source anythingllm

# 完全跳过知识库，仅用互联网检索
/taw output/ --chapter 1.3 --kb-source none

# 永久设置默认知识库路径（后续运行都使用）
/taw --set-kb /data/company-kb
```

---

## 执行流程详解

taw 的完整执行流程分为四个 Phase。

### Phase 0：输入与配置检测

```
用户命令
  ├─ 含 -h/--help? → 输出帮助文本，退出
  ├─ 含 --build-kb-index? → 扫描 KB 目录生成索引，退出
  ├─ 含 --set-kb? → 保存配置，退出
  └─ 正常撰写模式
       ├─ 文件路径解析
       ├─ KB 路径解析（优先级：--kb > 配置文件 > 首次运行引导）
       ├─ --kb-source 解析 → 知识库来源控制
       ├─ --vendor 解析 → VENDOR_NAME（必填，缺则报错引导用户配置）
       ├─ --query 解析 → EXTRA_QUERY（空则用默认模板）
       └─ --chapter 解析 → CHAPTERS_TO_WRITE 列表
```

### Phase 1：撰写准备

#### 评分映射与写作指导提取
- 从分析报告 **M4** 提取评分项，标注高分项（≥10 分）为重点展开
- 从分析报告 **M7** 提取关键词清单、写作策略、差异化亮点、红线约束

#### 知识库文字检索（四层）
`--kb-source none` 时跳过第一至三层，直接进入第四层。

```
第一层 fixed（原文照搬）
  触发：章节涉及"售后/维保/质保"等固定条款
  命中 → 原文照搬，标注 [来源：固定条款，不可修改]
  ↓ 未命中

第二层 reusable（微调复用）
  触发：任何章节（与 fixed 并行检查）
  命中 → 读取文件，微调后写入（取最相关 1-2 条）
  ↓ 未命中

第三层 history（参考提炼）
  触发：第二层无命中
  命中 → 按 key_sections.pages 精准读取，应用脱敏映射后改写
  ↓ 未命中

第四层 WebSearch 兜底
  触发：前三层均无命中，或 --kb-source none
  上限：≤ 2 次/节（--kb-source none 时 ≤ 3 次/节）
```

#### 图片获取（优先级链）

```
--image-source auto 模式：
按三级章节（H3）粒度，根据每个子节内容上下文独立选择图片来源（drawio/ai/web/placeholder）
同一 H2 章节下的不同 H3 子节可选择不同来源

指定模式（如 --image-source ai）：
仅尝试指定来源，失败后直接使用占位符
```

### Phase 2：内容生成

- **单节模式**：直接生成，输出 `drafts/1.3_总体方案设计.docx`
- **多节模式**：按序循环，每节完成显示进度，所有节合并为单 DOCX 文件

### Phase 3：质量自检与输出

每节生成后自动执行基础自检，输出自检报告。

---

## 知识库配置

taw 使用 `Local-KnowledgeBase/` 目录结构（每个文档为主文档 .md + `images/` 子目录），索引器自动发现目录中的 .md 文件（优先匹配 `full.md`，兼容任意文件名）。通过 `python kb_indexer.py --scan` 生成 `kb_catalog.yaml` 索引。

### 首次配置

首次运行时，taw 会引导配置知识库路径。

### 修改配置

```bash
# 永久修改默认知识库路径
/taw --set-kb /data/company-kb

# 验证配置
cat ~/.config/tender-workflow/config.yaml
```

### 临时覆盖

```bash
# 本次运行使用指定路径，不修改配置文件
/taw --outline output/ --report output/ --chapter 1.3 --kb /tmp/test-kb
```

---

## 知识库索引构建

知识库索引由 `skills/taw/tools/kb_indexer.py` 自动生成。

```bash
# 生成 Local-KnowledgeBase 目录索引
/taw --build-kb-index
python skills/taw/tools/kb_indexer.py --scan
```

---

## 章节号格式详解

taw 支持四种章节指定方式。

### 全章节序列

```
一（1）→ 1.1  1.2  1.3  1.4  1.5  1.6  1.7  1.8  1.9  1.10  1.11
```

### 格式一：单节

```bash
/taw output/ --chapter 1.3    # 撰写 1.3 总体方案设计
/taw output/ --chapter 1.10   # 撰写 1.10 售后服务方案
```

### 格式二：整章

```bash
/taw output/ --chapter 一     # 撰写技术部分全部 11 节（1.1-1.11）
/taw output/ --chapter 1      # 同上，数字别名
```

### 格式三：范围

```bash
/taw output/ --chapter 1.1-1.9      # 从 1.1 到 1.9，共 9 节
/taw output/ --chapter 1.1 到 1.9     # 同上，中文"到"
```

### 格式四：全部

```bash
/taw output/ --chapter all    # 撰写全部 11 节
```

---

## 使用场景范例

### 场景一：日常单章节撰写（目录简写）

```bash
/taw output/ --chapter 1.3
```

### 场景二：批量撰写技术部分（显式路径）

```bash
/taw --outline output/投标文件大纲_20260305.docx --report output/招标分析报告_20260305.md --chapter 一
```

### 场景三：范围撰写

```bash
/taw output/ --chapter 1.1 到 1.9
```

### 场景四：多厂商视角切换（--vendor）

```bash
# 以博云视角撰写技术章节
/taw output/ --chapter 1.3 --vendor "博云"
```

### 场景五：自定义搜索词（--query）

```bash
/taw output/ --chapter 1.7 --query "等保 2.0 容器安全 零信任架构"
```

### 场景六：图片来源控制

```bash
# 使用 AI 生成图片
/taw output/ --chapter 1.3 --image-source ai

# 使用 draw.io 生成图表
/taw output/ --chapter 1.3 --image-source drawio

# 自动选择（默认，按 H3 子节上下文动态选择）
/taw output/ --chapter 1.3
```

### 场景七：无知识库，依赖互联网检索

```bash
/taw output/ --chapter 1.3 --kb-source none
```

### 场景八：MCP 搜索工具选择

```bash
# 强制使用 Tavily Search
/taw output/ --chapter 1.3 --search-tool tavily

# 强制使用 Exa Search
/taw output/ --chapter 1.3 --search-tool exa

# 自动选择（默认）
/taw output/ --chapter 1.3
```

### 场景九：自定义字数和图片配额

```bash
# 二级章节 6000 字，三级子节 1200 字
/taw output/ --chapter 1.3 --l2-words 6000 --l3-words 1200

# 四级/五级子节字数自定义
/taw output/ --chapter 1.11 --l4-words 800 --l5-words 500

# 图片配额自定义：二级章节 3 张，三级子节各 1 张
/taw output/ --chapter 1.3 --l2-images 3 --l3-images 1

# 组合使用：增加字数 + 增加图片
/taw output/ --chapter 1.3 --l2-words 6000 --l2-images 4
```

---

## 输出文件说明

### 文件位置

输出路径：`./drafts/`

### 文件命名规则

| 模式 | 命名格式 | 示例 |
|------|---------|------|
| 单节 | `<节号>_<节名>.docx` | `1.3_总体方案设计.docx` |
| 整章 | `<起始节>-<结束节>_合并.docx` | `1.1-1.11_合并.docx` |
| 范围 | `<起始节>-<结束节>_合并.docx` | `1.1-1.9_合并.docx` |

---

## 工作流集成

taw 是四角色招投标工作流的第三环节：

```
tpl（策划者）  →  招标文件
                      ↓
              taa（分析者）  →  招标分析报告 + 投标文件大纲
                                        ↓
                              taw（撰稿者）  →  章节草稿 DOCX
                                                      ↓
                                          trv（审核者）  →  审核报告
```

### 与 taa 的衔接

```bash
# taa 产出
output/招标分析报告_YYYYMMDD.md
output/投标文件大纲_YYYYMMDD.docx

# taw 调用
/taw output/ --chapter 1.3
```

### 与 trv 的衔接

```bash
# 单章节审核
/trv drafts/5.3_总体方案设计.docx --type chapter --reference output/招标分析报告.md
```

---

## 质量保证机制

每个章节生成后自动执行基础自检：

| 自检项 | 通过标准 |
|--------|---------|
| 评分覆盖度 | M4 相关评分点 100% 有实质性响应 |
| M7 关键词覆盖率 | ≥ 80% |
| 废标红线 | M5 条款和 M7.5 红线零违反 |
| 过度承诺检测 | 零绝对化措辞 |
| 待确认标注 | 无支撑内容全部标注 |

---

## 常见问题

**Q：运行后提示找不到分析报告或大纲怎么办？**

使用 `--outline` 和 `--report` 显式指定文件。若尚未生成，请先运行 `/taa <招标文件>`。

**Q：知识库匹配结果为 0，正常吗？**

正常。taw 会自动触发互联网检索兜底，生成的内容中具体数据会标注 `[互联网来源，请核实]`。

**Q：--kb-source 和 --kb 有什么区别？**

- `--kb-source` 控制**来源类型**（AnythingLLM/本地索引/无）
- `--kb` 指定**具体路径**（临时覆盖配置文件）

**Q：生成的内容太通用，不够针对本项目？**

检查分析报告中 M7 模块是否完整，或通过 `--query` 传入更精准的搜索词。

**Q：如何配置 AI 图片生成 API Key？**

```bash
# 环境变量（推荐）
export ARK_API_KEY="sk-xxxxx"

# 或配置文件
echo "ark_api_key: sk-xxxxx" >> ~/.config/tender-workflow/config.yaml
```

---

*taw v3.0.0 | 投标文件撰稿助手*
