---
name: trv
description: >
  **甲方+乙方双视角的审核器**。当用户说"审核标书"、"审一下标书"、"检查投标文件"、"审查招标文件"、
  "审核方案"、"review"、"quality check" 时触发。多维度审核（完整性 / 合规性 / 评分对齐 / 风险检查），
  支持 AI 驱动智能修订。审核类型 --type 与视角对应：
  `tender_doc`（甲方视角，审 /tpl 产出的招标技术规格与评标办法本身的质量）；
  `analysis` / `outline` / `chapter` / `full_bid`（乙方视角，审 /taa /taw 产出的投标内容）。
  互斥提示：若用户要求**理解招标需求、评估投标可行性**而非"审核质量"，应使用 /taa 而非本 skill。
disable-model-invocation: false
allowed-tools: Read, Write, Bash, Glob, Grep
---

> **跨平台兼容性 checklist**（Windows / macOS / Linux）：
> 1. **Python 命令名**：示例用 `python3`。Windows 不可识别时改 `python` 或 `py -3`。
> 2. **路径自定位**：本文档所有脚本路径用下方 §路径自定位 一节的 bootstrap 解析（替代 `$SKILL_DIR`）。
> 3. **可执行检测**：用 `which`/`where`/`Get-Command`，不用 `command -v`。
> 4. **Bash heredoc / `&&` / `||`**：Windows cmd 不支持，建议在 Git Bash / WSL2 中运行。
> 5. **路径分隔符**：用正斜杠 `/`，避免硬编码反斜杠 `\`。

<SUBAGENT-STOP>
此技能是给协调者读的。**判定你是否子智能体**：如果你的当前角色定义来自 Task prompt 而非 SKILL.md 自然加载（即调用方在 Task 工具的 prompt 字段里塞了 agents/<role>.md 的内容），你就是子智能体；跳过本 SKILL.md 的工作流编排部分，只执行 Task prompt 给你的具体任务。
</SUBAGENT-STOP>

## 路径自定位

**首次调用本 skill 的脚本/工具前，先跑一次以下 bootstrap 解析 SKILL_DIR**（后续命令用 `$SKILL_DIR/tools/...`、`$SKILL_DIR/prompts/...`、`$SKILL_DIR/templates/...`）：

```bash
SKILL_DIR=$(python3 - <<'PYEOF' 2>/dev/null
import json, os, sys
p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(p):
    d = json.load(open(p))
    for entries in d.get('plugins', {}).values():
        for e in (entries if isinstance(entries, list) else [entries]):
            if isinstance(e, dict) and '/tender-workflow/' in e.get('installPath', ''):
                print(e['installPath'] + '/skills/trv'); sys.exit(0)
PYEOF
)

# vercel CLI fallback
[ -z "$SKILL_DIR" ] && for d in ~/.cursor/skills ~/.agents/skills .cursor/skills .agents/skills; do
    [ -d "$d/tender-workflow/skills/trv" ] && SKILL_DIR="$d/tender-workflow/skills/trv" && break
    [ -d "$d/trv" ] && SKILL_DIR="$d/trv" && break
done

# 用户预设环境变量
[ -z "$SKILL_DIR" ] && [ -n "${TENDER_WORKFLOW_PLUGIN_PATH:-}" ] && SKILL_DIR="$TENDER_WORKFLOW_PLUGIN_PATH/skills/trv"

# dev 态
[ -z "$SKILL_DIR" ] && [ -d "./tender-workflow/skills/trv" ] && SKILL_DIR="$(pwd)/tender-workflow/skills/trv"

if [ -z "$SKILL_DIR" ]; then
    echo "[ERROR] 找不到 tender-workflow / trv skill 安装位置。" >&2
    echo "请设置：export TENDER_WORKFLOW_PLUGIN_PATH=/path/to/tender-workflow" >&2
    exit 1
fi
```

**错误恢复 protocol**：bootstrap 退出 1 时不要重试，把 stderr 转述给用户并请求 `/plugin install tender-workflow@presales-skills` 或手工 export 环境变量。


# 审核者 (TRV) - Tender Reviewer

对招标文件、分析报告、投标大纲、章节草稿、技术标书进行多维度审核。

## 角色定位

**服务对象**: 甲方 + 乙方（服务招投标全流程）
**核心任务**: 对各阶段产出物进行质量把控，识别问题与风险，提供改进建议

## 使用方式

```bash
/trv <file> --type <review_type> [--reference <file>] [--level <level>] [--focus <focus>] [--revise-docx] [--revise-scope <must|all>]
```

**参数说明**:
- `file`: 待审核的文件路径
- `--type`: 审核类型（必填）
  - `tender_doc`: 技术规格与评标办法审核（tpl v2.0 输出，含 M3 评标办法 + M5 技术规格）
  - `analysis`: 招标分析报告审核
  - `outline`: 投标大纲审核（技术部分）
  - `chapter`: 章节草稿审核
  - `full_bid`: 技术标书审核
- `--reference`: 参考文件（用于对照审核，可选但推荐）
  - 审核大纲时：引用招标分析报告
  - 审核章节时：引用招标分析报告
  - 审核完整标书时：引用招标文件
- `--level`: 审核严格程度（可选，默认`all`）
  - `critical`: 仅检查严重问题（快速检查）
  - `high`: 检查严重和高风险问题
  - `all`: 完整检查（包括建议优化项）
- `--focus`: 专注维度（可选）
  - `completeness`: 仅检查完整性
  - `compliance`: 仅检查合规性
  - `scoring`: 仅分析评分契合度
  - `risk`: 仅识别风险
  - `style`: 仅检查文风 / 反 AI 写作痕迹（**不计入默认 all**，需显式指定才启用；详见 `prompts/writing_style.yaml`）
- `--revise-docx`: 审核完成后自动生成修订版 DOCX（仅对 `.docx` 输入有效，优先支持 `outline` / `chapter` / `full_bid`）
- `--revise-scope`: 自动修订范围（可选，默认 `must`）
  - `must`: 仅处理必须修改项/严重和重要问题
  - `all`: 同时纳入建议优化项

**输出**: `output/trv/审核报告_<type>_<timestamp>.md`，启用 `--revise-docx` 时额外输出 `output/trv/<原文件名>_修订版_<timestamp>.docx`

---

## Phase 0：参数解析与初始化

### 0.0 参数解析

检查命令行参数并解析：

**步骤**：

1. **检查帮助参数**：
   - 如果参数包含 `-h` 或 `--help`，输出帮助信息并退出
   - 帮助信息包括：使用方式、参数说明、审核类型详解、使用示例

2. **解析位置参数**：
   - 第一个位置参数：待审核文件路径
   - 如果未提供，输出错误提示并退出

3. **解析 --type 参数**（必选）：
   - 检查是否提供 --type 参数
   - 验证 --type 值是否有效（tender_doc/analysis/outline/chapter/full_bid）
   - 如果未提供或无效，输出错误提示并退出

4. **解析 --reference 参数**（可选）：
   - 如果提供，检查文件是否存在
   - 如果文件不存在，输出警告但继续执行

5. **解析 --level 参数**（可选，默认 all）：
   - 验证值是否有效（critical/high/all）
   - 如果无效，输出警告并使用默认值 all

6. **解析 --focus 参数**（可选）：
   - 验证值是否有效（completeness/compliance/scoring/risk/style）
   - 如果无效，输出警告并忽略
   - **注意**：`style` 仅在显式指定时启用，**不计入默认全维度审核**（向后兼容，避免现存用户跑 trv 时评级突变）

7. **解析 --revise-docx 参数**（可选）：
   - 若提供该参数，记录 `REVISE_DOCX=true`
   - 若未提供，默认 `REVISE_DOCX=false`

8. **解析 --revise-scope 参数**（可选，默认 must）：
   - 验证值是否有效（must/all）
   - 如果无效，输出警告并使用默认值 `must`

9. **参数组合检查**：
   - 如果 --focus=scoring 但未提供 --reference，输出建议提示
   - 如果审核类型为 outline/chapter/full_bid 但未提供 --reference，输出建议提示
   - 如果启用 `--revise-docx` 但待审核文件不是 `.docx`，输出提示“自动修订已跳过：仅支持 DOCX 输入”并继续审核
   - 如果启用 `--revise-docx` 但审核类型不是 `outline`/`chapter`/`full_bid`，输出提示“当前类型暂不支持自动修订”，并继续审核

10. **输出参数解析摘要**：
   ```
   ========================================
   TRV 审核参数解析
   ========================================
   待审核文件: <file_path>
   审核类型: <type>
   参考文件: <reference_path> (如提供)
   审核级别: <level>
   专注维度: <focus> (如提供)
   自动修订: 开启/关闭
   修订范围: <revise_scope> (如启用)
   ========================================
   ```

### 0.05 配置加载（可选）

读取统一配置文件获取默认审核级别（可被 `--level` 参数覆盖）：
```bash
python3 $SKILL_DIR/../twc/tools/tw_config.py get trv default_level
```

- 若未指定 `--level` 且配置中 `trv.default_level` 有值 → 使用配置值
- 配置文件：`~/.config/tender-workflow/config.yaml`，通过 `/twc setup` 管理

### 0.1 输出目录初始化

确定输出路径：

**步骤**：

1. **设置输出路径**：
   ```bash
   OUTPUT_DIR="./output/trv"
   ```

2. **创建输出目录**：
   ```bash
   mkdir -p "${OUTPUT_DIR}"
   ```

3. **输出环境信息**：
   ```
   输出目录: ./output/trv
   ```

### 0.2 文件读取

读取待审核文件和参考文件：

**步骤**：

1. **读取待审核文件**：
   - 使用 Read 工具读取文件内容
   - 支持 PDF、DOCX、Markdown 格式
   - 如果读取失败，输出错误并退出

2. **读取参考文件**（如提供）：
   - 使用 Read 工具读取参考文件内容
   - 支持 PDF、DOCX、Markdown 格式
   - 如果读取失败，输出警告但继续执行

3. **输出文件信息摘要**：
   ```
   ========================================
   文件信息
   ========================================
   待审核文件: <file_name>
   文件类型: <file_type>
   文件大小: <file_size>
   参考文件: <reference_name> (如提供)
   ========================================
   ```

### 0.25 文档质量预检（DOCX 编码完整性检查与自动修复）

对 DOCX 格式的待审核文件，在进入正式审核前执行编码完整性扫描。若发现乱码，自动修复（最多重试 3 次）后再进入审核流程。

**执行条件**：待审核文件为 .docx 格式

**步骤**：

1. 执行 `python3 $SKILL_DIR/../twc/tools/docx_encoding_check.py --fix <file_path> --max-retries 3`

2. 根据退出码和输出判断结果：

   - **`FIX_OK`（退出码 0）**：无乱码或已全部清除。
     在审核报告"基本信息"中记录清除数量，使用修复后的文件继续审核。

   - **`FIX_FAILED`（退出码 2）**：3 次重试后仍有残留。
     将残留信息记录为 **critical 级别问题**，并**通知用户人工修复**：
     ```
     ⚠️ 文档编码损坏：3 次自动修复后仍残留 N 处乱码，需要人工介入。
     残留位置：<工具输出的 UNFIXED 列表>
     建议操作：
     1. 重新生成文档（推荐）
     2. 在 Word 中打开文件，手动修正上述段落
     修复完成后请重新提交审核。
     ```
     使用修复后的文件继续后续审核（尽量提供完整审核意见），但最终结论标注为"不通过"。

### 0.3 启动确认

输出审核启动信息并直接进入 Phase 1：

**输出**：
```
========================================
开始审核
========================================
审核类型: <type_name>
审核维度: <dimensions>
预计耗时: <estimated_time>
========================================
```

**预计耗时参考**：
- critical 级别：1-2 分钟
- high 级别：3-5 分钟
- all 级别：5-10 分钟

---

## Phase 1：多维度审核执行

### 1.0 确定审核维度

根据 --focus 参数确定执行的审核维度：

**步骤**：

1. **如果提供了 --focus 参数**：
   - 仅执行指定的维度（含 `style` 时执行 1.5 文风审核）
   - 输出：`审核维度: <focus_name>`

2. **如果未提供 --focus 参数**：
   - 执行默认 4 个维度（**不含 style**——向后兼容）
   - 输出：`审核维度: 完整性检查、合规性审查、评分契合度分析、风险识别`

3. **维度执行顺序**：
   - 1.1 完整性检查（Completeness）
   - 1.2 合规性审查（Compliance）
   - 1.3 评分契合度分析（Scoring Alignment）
   - 1.4 风险识别（Risk Check）
   - 1.5 文风审核（Writing Style，**仅 `--focus style` 时执行**）

### 1.0.1 上下文模式决策

根据待审核文件体量，自动选择审核模式：

**步骤**：

1. **估算内容 token 量**：
   - 对 DOCX/PDF 文件：使用 Bash 工具提取实际文本字符数（python3 -c "from docx import Document; print(sum(len(p.text) for p in Document('file.docx').paragraphs))"），然后 `估算 token = 字符数 × 1.5`
   - 对 Markdown/纯文本文件：使用 Bash 工具获取文件大小（字节数），`估算 token = 字节数 / 2`
   - 如果提供了 --reference，同样估算参考文件 token 量
   - `总估算 token = 待审核文件 token + 参考文件 token + 15000`（审核指令开销）
   - 注意：DOCX 文件字节数包含图片等二进制数据，不能直接用文件大小估算

2. **模式决策**：
   ```
   IF 总估算 token < 80000:
     → REVIEW_MODE = "inline"（当前内联模式，直接进入 1.1-1.4）
   
   ELIF type == "full_bid":
     → REVIEW_MODE = "chunked"（分块审核模式，进入 1.0.2）
   
   ELIF type == "chapter" AND 总估算 token >= 80000:
     → REVIEW_MODE = "chunked_chapter"（大章节分块模式，进入 1.0.2）
   
   ELSE:
     → REVIEW_MODE = "inline"
   ```

3. **输出模式信息**：
   ```
   审核模式: <mode>（内联/分块审核/大章节分块）
   估算 token: <estimated_tokens>
   ```

4. **如果 REVIEW_MODE == "inline"**：跳过 1.0.2-1.0.5，直接进入 1.1（按下方 §1.1 路由）

---

### 1.0.2-1.0.5 分块审核 Phase A/B/C/D（chunked 模式专用）

`REVIEW_MODE == "chunked"` 或 `"chunked_chapter"` 时执行。完整流程（动态分块规划、子 Agent 并行调度、跨 chunk 一致性检查、结果汇总、降级守卫）见 **`references/chunked-review-mode.md`**。

核心要点：

- Phase A 按 L2 章节切分，> 30000 字章节自动下沉 L3
- Phase B 每批最多 4 个 Agent 并行，> 50% 失败时降级保留已完成结果
- Phase C 跨 chunk 一致性检查（数值/描述/承诺矛盾）
- Phase D 合并去重 + 标注分块审核信息

### 1.1-1.4 内联审核 4 维度（inline 模式）

`REVIEW_MODE == "inline"` 时执行 4 个维度（按 `--focus` 选择）：完整性 / 合规性 / 评分契合度 / 风险识别。每个维度的检查清单加载、分级过滤、Markdown 输出表格模板见 **`references/inline-review-dimensions.md`**。

| 维度 | --focus 值 | prompts/*.yaml | 输出表格主键 |
|---|---|---|---|
| 1.1 完整性 | `completeness` | completeness.yaml | 检查项 / 状态 / 严重程度 |
| 1.2 合规性 | `compliance` | compliance.yaml | 审查项 / 合规状态 / 法规引用 |
| 1.3 评分契合度 | `scoring` | scoring_alignment.yaml | 评分项 / 覆盖程度 / 匹配度 |
| 1.4 风险识别 | `risk` | risk_check.yaml | 风险分类 / 等级 / 应对措施 |
| 1.5 文风审核 | `style` | writing_style.yaml | AI 痕迹类别 / severity / 5 维评分 |

未指定 `--focus` = 默认执行 1.1-1.4 这 4 维度（**不含 1.5 style**）。要审文风必须显式 `--focus style`。

**1.5 文风审核执行要点**：

- 仅在 `--focus style` 时执行
- 加载 `prompts/writing_style.yaml` 的 4 大类（ai_traces / formality / rhythm / word_choice）+ 5 维评分
- 输出独立段落"## 文风审核（writing_style）"嵌入审核报告，含每项检出位置 + 原文 + 改写建议
- 评分判定：≥45 分（A，优秀）/ 35-44（B，良好）/ <35（C/D，需修订）
- 与 1.1-1.4 正交：1.1-1.4 审"内容是否对、是否完整、是否合规"，1.5 审"语言是否像 AI 生成"

---

## Phase 2：审核结果汇总

汇总各维度结果，生成 3 个固定模板输出（结论 / 问题清单 / 修改优先级）。完整模板见 **`references/output-templates.md` §2.1-2.3**。

核心规则：

- §2.1 总体评价判定：通过（无 critical, major ≤ 3）/ 有条件通过（无 critical, major > 3）/ 不通过（有 critical）
- §2.2 问题清单按 critical / major / minor 分组
- §2.3 修改优先级用 `- [ ]` checkbox 形式（必须修改 / 建议修改 / 可选优化）

---

## Phase 3：Markdown 报告生成

### 3.1-3.2 报告模板与文件保存

完整报告 Markdown 模板（基本信息 / 审核结论 / 详细审核结果 / 问题清单 / 修改优先级 / 附录）+ 文件命名规则（`审核报告_<type>_<timestamp>.md`）+ 保存逻辑见 **`references/output-templates.md` §3.1-3.2**。

### 3.5 DOCX 智能修订（仅 --revise-docx）

启用 `--revise-docx` 且原文为 `.docx` 且 `--type` ∈ `{outline, chapter, full_bid}` 时执行。AI 动态生成修订指令 JSON → `trv_docx_reviser.py` 执行 → 编码检查。完整流程（6 种指令类型、5 种匹配方式、表格 header_row 定位、失败降级、结果报告）见 **`references/docx-revision-ai-driven.md`**。

不传 `--revise-docx`、非 .docx、或 `--type` 为 tender_doc / analysis 时**直接跳过本步**。

---

## Phase 4：任务完成与清理

### 4.1 输出确认

```
✅ 审核完成！已生成：
报告文件: <报告路径>
审核类型: <type>
审核级别: <level>
[修订版文件: <path>]（仅 --revise-docx 成功时）
```

### 4.2 审核结果摘要

输出 Phase 2.1 的总体评价 + 严重程度分布。

### 4.3 后续建议

根据总体评价给出建议：

- **通过** → 可直接交付/发布
- **有条件通过** → 修复 §2.3 "建议修改" 项后再交付
- **不通过** → 必须修复 §2.3 "必须修改" 项

### 4.4 文件交付

告知用户报告路径、修订版路径（如有）、临时文件清理状态。

---

## Gotchas（真坑沉淀，AI 高频犯错）

| Gotcha | 后果 | 正确做法 |
|---|---|---|
| **DOCX token 估算用文件大小** | DOCX 含图片/二进制，文件大小 ≠ 文本量；估算虚高，本该 inline 的小标书被错误送进分块流程 | 必须用 `python3 -c "from docx import Document; print(sum(len(p.text) for p in Document('file.docx').paragraphs))"` 提取**纯文本字符数**，再 `× 1.5` 估 token |
| **chapter_h3_chunk 模式越界评判** | H3 子 Agent 评判整章节需求/评分覆盖度 → 重复结论 + 与 Phase C 章节级评估冲突 | H3 子 Agent 只评 H3 主题；章节级评估由 Phase C 一致性检查统一做 |
| **--revise-docx 失败回滚审核报告** | 用户拿不到任何输出 | 修订工具/编码检查失败时**不能回滚审核报告**，照常交付 .md，仅在终端追加"修订失败"提示（见 `references/docx-revision-ai-driven.md` §5） |
| **表格修订硬编码行索引** | 招标方调一行表格顺序 → 修订全错位 | 必须用 `table_header_row` 匹配（按表头列名 + 行标识值定位），禁止用行号 |
| **审核结论"通过"判定阈值搞反** | 漏判一般问题 > 3 项时仍报"通过" | 通过 = **无 critical 且 major ≤ 3**；只要 major > 3 就是"有条件通过"（详见 `references/output-templates.md` §2.1） |
| **inline 模式跑分块流程** | 浪费 4 个 Agent 名额 + 无意义一致性检查 | §1.0.1 决策后必须严格按 REVIEW_MODE 路由：inline → 跳到 1.1；chunked* → 跳到 1.0.2 |

---

## 执行示例 / 错误处理 / 注意事项

5 个 `--type` 场景的完整执行示例（tender_doc / outline / chapter / full_bid / 含 --revise-docx）+ 错误处理矩阵（参数 / 文件读取 / 审核执行 / 文件保存 / 智能修订 5 类）+ 5 项使用注意事项见 **`references/usage-examples-troubleshooting.md`**。

## 版本历史

详见 `tender-workflow/CHANGELOG.md` §trv 部分（v1.0.0 - v1.5.0）。

