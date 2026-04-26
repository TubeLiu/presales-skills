---
name: tpl
description: >
  当用户提供产品功能清单或描述，要求生成招标技术规格与要求时自动调用。
  。将产品功能清单转换为无控标痕迹的招标技术规格与评标办法，
  输出 DOCX 格式。支持 --template 指定行业模板，--level 控制细致程度。
disable-model-invocation: false
allowed-tools: Read, Write, Bash, Glob
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
SKILL_DIR=$(python3 -c "
import json, os, sys
p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(p):
    d = json.load(open(p))
    for entries in d.get('plugins', {}).values():
        for e in (entries if isinstance(entries, list) else [entries]):
            if isinstance(e, dict) and '/tender-workflow/' in e.get('installPath', ''):
                print(e['installPath'] + '/skills/tpl'); sys.exit(0)
" 2>/dev/null)

# vercel CLI fallback
[ -z "$SKILL_DIR" ] && for d in ~/.cursor/skills ~/.agents/skills .cursor/skills .agents/skills; do
    [ -d "$d/tender-workflow/skills/tpl" ] && SKILL_DIR="$d/tender-workflow/skills/tpl" && break
    [ -d "$d/tpl" ] && SKILL_DIR="$d/tpl" && break
done

# 用户预设环境变量
[ -z "$SKILL_DIR" ] && [ -n "${TENDER_WORKFLOW_PLUGIN_PATH:-}" ] && SKILL_DIR="$TENDER_WORKFLOW_PLUGIN_PATH/skills/tpl"

# dev 态
[ -z "$SKILL_DIR" ] && [ -d "./tender-workflow/skills/tpl" ] && SKILL_DIR="$(pwd)/tender-workflow/skills/tpl"

if [ -z "$SKILL_DIR" ]; then
    echo "[ERROR] 找不到 tender-workflow / tpl skill 安装位置。" >&2
    echo "请设置：export TENDER_WORKFLOW_PLUGIN_PATH=/path/to/tender-workflow" >&2
    exit 1
fi
```

**错误恢复 protocol**：bootstrap 退出 1 时不要重试，把 stderr 转述给用户并请求 `/plugin install tender-workflow@presales-skills` 或手工 export 环境变量。


# 策划者 (TPL) v2.0 - Tender Planner

帮助甲方将产品功能清单转换为招标技术规格与评标办法。

## 角色定位

**服务对象**: 甲方（招标方）
**核心任务**: 将乙方产品功能清单，自然地、无控标痕迹地转换为甲方视角的招标技术规格与评标办法
**核心能力**: 反控标转换（术语中性化、指标合理化、需求泛化、分布均衡）

## 使用方式

```bash
/tpl <产品功能清单> [--project <项目概述>] --template <行业> [--level <级别>] [--no-scoring]
```

**参数说明**:
- `<产品功能清单>`: 必选（或使用 `--kb`）。产品功能文件（.txt/.md/.xlsx/.pdf）
- `--kb`: 可选。使用知识库产品索引，可与文件输入组合
- `--project <file>`: 可选。项目概述（背景、预算、规模），不传则生成纯技术规格
- `--template`: 必选。行业类型
  - `government`: 政府行业（含信创/国产化/等保要求）
  - `finance`: 金融行业（含金融级安全/高可用/两地三中心）
  - `soe`: 央国企（含自主可控/长期支持/国产化替代）
  - `enterprise`: 通用企业（灵活部署/快速交付/成本优化）
  - `government_it`: 已废弃，自动映射到 government
  - `goods_procurement`: 已废弃，自动映射到 enterprise
  - `service_procurement`: 已废弃，自动映射到 enterprise
- `--level`: 可选。细致程度（默认 standard）
  - `detailed`: 详细（40-60 条要求，15-20 页，适用大型项目 >500 万）
  - `standard`: 普通（15-25 条要求，8-12 页，适用中型项目 100-500 万）
  - `general`: 一般（8-12 条要求，4-6 页，适用小型项目 50-100 万）
  - `brief`: 简略（5-8 条要求，2-3 页，适用 <50 万或内部参考）
- `--no-scoring`: 可选。跳过评标办法，只输出技术规格
- `-h, --help`: 显示帮助信息

**输出**:
- 默认：`output/tpl/技术规格与评标办法_<项目名>_<timestamp>.docx`
- 加 `--no-scoring`：`output/tpl/技术规格_<项目名>_<timestamp>.docx`

**示例**:
```bash
# 政府行业标准技术规格与评标办法
/tpl features.txt --template government

# 金融行业详细技术规格，含项目背景
/tpl features.txt --project overview.txt --template finance --level detailed

# 使用知识库产品索引，简略输出
/tpl --kb --template soe --level brief

# 组合输入（文件+知识库），不生成评标办法
/tpl features.txt --kb --template enterprise --no-scoring

# 查看帮助
/tpl -h
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 0: 参数解析与输入加载                                    │
│     ├── 解析命令参数                                          │
│     ├── 读取产品功能清单（文件/KB 索引）                         │
│     ├── 读取项目概述（可选）                                    │
│     └── 加载行业模板                                          │
├─────────────────────────────────────────────────────────────┤
│  Phase 1: 产品功能分析                                         │
│     ├── 解析并分类所有产品功能                                   │
│     ├── 识别控标点条目                                         │
│     ├── 提取量化指标                                          │
│     └── 构建功能注册表                                         │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: 反控标转换（核心）                                    │
│     ├── 术语中性化（去品牌/产品名）                              │
│     ├── 指标合理化（下限表达/浮动调整）                           │
│     ├── 需求泛化（功能结果导向）                                 │
│     ├── 分布均衡（多域覆盖/等级分配）                            │
│     └── 反控标自检                                            │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: 技术规格生成                                         │
│     ├── 按 level 生成对应深度的内容                              │
│     ├── 叠加行业模板专项章节                                    │
│     └── 内部一致性检查                                         │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: 评标办法生成（除非 --no-scoring）                      │
│     ├── 从技术规格自动映射技术评分维度                            │
│     ├── 加载模板权重和商务评分                                   │
│     └── 交叉检查：必须项↔评分项对应                              │
├─────────────────────────────────────────────────────────────┤
│  Phase 5: DOCX 输出与交付                                      │
│     ├── 生成 DOCX 格式文件                                     │
│     ├── 反控标最终检查                                         │
│     └── 输出确认和建议                                         │
└─────────────────────────────────────────────────────────────┘
```

## Prompt 框架

- `prompts/anti_control.yaml` - 反控标转换规则（提示词驱动，含控标点规则）
- `prompts/level_rules.yaml` - 四级细致程度定义
- `prompts/technical.yaml` - 技术规格编写
- `prompts/scoring.yaml` - 评标办法设计

---

## Phase 0：参数解析与输入加载

### 0.0 参数解析

**步骤一：检测帮助参数**

若用户指令包含 `-h` 或 `--help` → 输出以下帮助信息后退出：

```
tpl v2.0 - 招标技术规格与评标办法生成工具

用法：
  /tpl <产品功能清单> [--project <项目概述>] --template <行业> [--level <级别>] [--no-scoring]

参数说明：
  <产品功能清单>       必选（或 --kb）。产品功能文件（.txt/.md/.xlsx/.pdf）

选项：
  --kb                 使用知识库产品索引，可与文件输入组合使用
  --project <file>     可选。项目概述（背景、预算、规模）
  --template <行业>    必选。指定行业类型
                       • government: 政府行业（信创/等保）
                       • finance: 金融行业（金融级安全/高可用）
                       • soe: 央国企（自主可控/长期支持）
                       • enterprise: 通用企业（灵活/快速交付）
  --level <级别>       可选。细致程度（默认 standard）
                       • detailed: 详细（40-60 条，15-20 页）
                       • standard: 普通（15-25 条，8-12 页）
                       • general: 一般（8-12 条，4-6 页）
                       • brief: 简略（5-8 条，2-3 页）
  --no-scoring         可选。跳过评标办法，只生成技术规格
  -h, --help           显示此帮助信息

示例：
  /tpl features.txt --template government
  /tpl features.txt --project overview.txt --template finance --level detailed
  /tpl --kb --template soe --level brief
  /tpl features.txt --kb --template enterprise --no-scoring

输出：
  output/tpl/技术规格与评标办法_<项目名>_<时间戳>.docx
  output/tpl/技术规格_<项目名>_<时间戳>.docx  (--no-scoring)
```

**步骤二：解析参数**

从用户指令中解析以下参数：

1. **产品功能清单**（位置参数，必选 —— 除非使用 `--kb`）
2. **`--kb`**（可选）：使用知识库产品索引
3. **`--project`**（可选）：项目概述文件
4. **`--template`**（必选）：行业类型
5. **`--level`**（可选，默认 `standard`）：细致程度
6. **`--no-scoring`**（可选）：跳过评标办法

**步骤三：参数验证**

1. **输入来源检查**：
   - 若既无位置参数也无 `--kb` → 输出错误并退出：
     ```
     错误：缺少产品功能清单输入

     用法：/tpl <产品功能清单> --template <行业>
     或：  /tpl --kb --template <行业>

     请使用 /tpl -h 查看详细帮助
     ```

2. **文件存在性检查**：
   - 若指定了位置参数但文件不存在 → 输出错误并退出
   - 若指定了 `--project` 但文件不存在 → 输出错误并退出

3. **`--template` 参数检查与映射**：
   - 若未提供 → 输出错误并退出，列出可用行业类型
   - 若为旧名称 → 自动映射并输出警告：
     - `government_it` → `government`
     - `goods_procurement` → `enterprise`
     - `service_procurement` → `enterprise`
   - 若无效 → 输出错误并退出

4. **`--level` 参数检查**：
   - 有效值：`detailed`, `standard`, `general`, `brief`
   - 若无效 → 输出错误并退出

**步骤四：参数解析完成宣告**

```
参数解析完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 产品功能来源：<文件名> / 知识库索引 / 文件+知识库
• 项目概述：<文件名> / 未提供
• 行业模板：<行业类型>
• 细致程度：<级别>
• 评标办法：生成 / 跳过
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 0.05 配置加载（可选）

读取统一配置文件获取默认值（可被命令行参数覆盖）：
```bash
python3 $SKILL_DIR/../twc/tools/tw_config.py get tpl default_template
python3 $SKILL_DIR/../twc/tools/tw_config.py get tpl default_level
```

- 若未指定 `--template` 且配置中 `tpl.default_template` 有值 → 使用配置值作为默认模板
- 若未指定 `--level` 且配置中 `tpl.default_level` 有值 → 使用配置值作为默认级别
- 配置文件：`~/.config/tender-workflow/config.yaml`，通过 `/twc setup` 管理

### 0.1 输出目录初始化

文件保存到 `./output/tpl/`。

### 0.2 输入加载

**步骤一：读取产品功能清单**

根据输入来源读取产品功能信息：

**文件输入**：
- 读取文件内容，提取功能条目
- 支持格式：.txt（每行一条功能）、.md（标题为分类，列表项为功能）、.xlsx（按列解析）、.pdf（提取文本）

**知识库索引（`--kb`）**：
- 按 level 执行分层加载：
  1. 读取产品索引 L0 文件（`product_l0.yaml`，~2KB，11 个分类）
  2. 根据 `--template` 和 `--project` 上下文，选择相关 L1 分类（通常 3-6 个）
  3. 按 level 决定加载深度：
     - `detailed`: 加载所有相关分类的 L2 完整详情
     - `standard`: 加载 Top 3 分类的 L2，其余使用 L1 摘要
     - `general`: 仅使用 L1 分类摘要
     - `brief`: 仅使用 L0 分类概述

**组合输入（文件 + `--kb`）**：
- 先加载知识库索引作为基础功能集
- 再读取文件内容作为补充/覆盖
- 文件中的功能条目优先于知识库条目

**步骤二：读取项目概述（可选）**

若提供了 `--project` 参数，读取文件内容提取：
- 项目名称（用于文件命名）
- 项目背景、建设目标
- 预算金额、资金来源
- 工期要求
- 特殊约束（等保、信创等）

若未提供，使用行业模板默认值，项目名称使用日期。

**步骤三：加载行业模板**

读取 `templates/<industry>.yaml`，获取：
- `characteristics`：行业特征（权重、核心关注点）
- `tech_spec_defaults`：技术规格默认框架（章节结构、行业专项章节）
- `scoring_defaults`：评标办法默认配置（权重、商务评分、技术评分提示）
- `anti_control_overrides`：行业反控标覆盖配置（允许术语、标准引用、指标敏感度）

### 0.3 启动确认

```
招标技术规格生成启动
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
项目名称：[项目名称或日期]
行业类型：[行业类型]
细致程度：[级别]
输出内容：技术规格 [+ 评标办法]
输出文件：技术规格[与评标办法]_[名称]_[时间戳].docx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

直接进入 Phase 1（无需用户回复）。

---

## Phase 1：产品功能分析

读取 `prompts/anti_control.yaml` 中的**控标点强制纳入规则**。

### 1.1 功能清单解析

对所有输入的产品功能条目执行：

1. **控标点识别**：扫描每条功能描述，若包含"控标点"三个字 → 标记 `is_control_point: true`
2. **功能分类**：按技术域分类（功能/性能/安全/集成/可靠性/交付/实施/服务）
3. **量化指标提取**：提取具体数值（如"10000 Pod"、"99.99%"、"P99 < 50ms"等）
4. **功能分级**：核心 / 标准 / 高级 / 可选

### 1.2 功能分析摘要

```
功能分析完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 总功能条目：X 条
• 控标点条目：Y 条（必须纳入）
• 技术域覆盖：Z 个
• 量化指标：W 项
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 2：反控标转换（核心）

读取 `prompts/anti_control.yaml` 完整配置和 `prompts/level_rules.yaml`。

这是 tpl v2.0 的核心阶段。按 `anti_control.yaml` 的提示词指令，引导 AI 模型执行以下转换。**所有转换逻辑通过提示词驱动，不硬编码具体映射规则，充分利用 AI 模型的语言理解和行业知识。**

### 2.1 控标点条目预处理

- 提取所有 `is_control_point: true` 的条目
- 这些条目在后续转换中**保留核心技术指标和功能要求的实质内容**
- 仅执行术语中性化（去品牌名），不降级指标、不合并、不省略

### 2.2 术语中性化

按 `anti_control.yaml` 的 `terminology_neutralization` 指令：
- 以甲方视角重新描述所有技术需求
- 去除产品名、品牌名、公司名、专有特性名
- 使用行业通用术语（CNCF/ISO/等保），参考行业模板的 `anti_control_overrides.allowed_specific_terms`

### 2.3 指标合理化

按 `anti_control.yaml` 的 `metric_rationalization` 指令：
- 使用下限表达（"不低于"、"应不少于"）
- 数值略低于产品实际能力（浮动 70%-85%，避免规律性）
- **控标点条目的量化指标保持原值不降级**
- 参考行业模板的 `anti_control_overrides.metric_sensitivity`

### 2.4 需求泛化

按 `anti_control.yaml` 的 `requirement_generalization` 指令：
- 具体实现方案 → 功能性需求描述
- 加入"或同等"、"或兼容方案"表述
- 按 `level_rules.yaml` 的压缩比合并相近功能（控标点条目不合并）

### 2.5 分布均衡

按 `anti_control.yaml` 的 `distribution_balance` 指令：
- 确保覆盖多个技术域
- 分配要求等级比例：实质性要求约 15-25% / 一般要求约 75-85%（加分区分交给评分细则）
- 适当补充来自行业最佳实践的通用要求

### 2.6 反控标自检

按 `anti_control.yaml` 的 `self_check` 指令：
- 品牌残留检查（零容忍）
- 分布集中度检查（单一域不超 40%）
- 要求等级比例检查
- 自然度评估

输出自检报告：
```
反控标自检报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 品牌残留：✅ 无 / ⚠️ 已修正 N 处
• 分布集中度：✅ 均衡 / ⚠️ 已调整
• 要求等级比例：实质性要求 X% / 一般要求 Y%
• 自然度评估：✅ 通过 / ⚠️ 已修正 N 处
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 3：技术规格生成

读取 `prompts/technical.yaml` 获取章节结构和写作规则。

### 3.1 章节结构组织

按 `technical.yaml` 的 sections 结构，将 Phase 2 转换后的要求组织为技术规格章节：

1. 项目总体说明
2. 功能需求规格（核心章节，反控标转换主要应用区域）
3. 性能需求规格
4. 接口与集成要求
5. 安全要求
6. **[行业专项章节]**（从行业模板 `tech_spec_defaults.sections` 动态插入）
7. 质量与可靠性要求
8. 交付物要求
9. 实施与服务要求
10. 验收标准

### 3.2 Level 控制

按 `level_rules.yaml` 控制每个章节的内容深度：
- `detailed`：逐项展开，每条附验收标准
- `standard`：核心详细，次要归组
- `general`：按类概括
- `brief`：扁平列表

### 3.3 行业专项注入

根据行业模板的 `tech_spec_defaults.sections`，在安全要求之后插入行业专项章节：
- **government**：等保安全要求、国产化/信创要求
- **finance**：金融级高可用架构要求、金融级安全要求、监管合规要求
- **soe**：自主可控技术路线要求、国产化适配要求、长期技术支持要求
- **enterprise**：灵活部署要求、快速交付要求、成本优化要求

### 3.4 内部一致性检查

- 章节编号连续无遗漏
- 交叉引用正确
- 要求表述风格统一（实质性要求/一般要求表述方式一致）

---

## Phase 4：评标办法生成

**除非指定 `--no-scoring`，否则执行此 Phase。**

读取 `prompts/scoring.yaml` 获取评标办法结构和生成规则。

### 4.1 评标方法确定

从行业模板获取：
- 评标方法（综合评分法/最低价法）
- 权重分配（价格/商务/技术）

### 4.2 技术评分维度映射

从 Phase 3 技术规格输出中自动映射：
- 每个主要章节 → 一个技术评分维度
- 量化要求 → 客观评分项
- 描述性要求 → 主观评分项（优/良/一般/较差四档）
- 控标点对应的维度分值适当提高

维度数量按 level：
- `detailed`: 6-8 个维度
- `standard`: 4-6 个维度
- `general`: 3-4 个维度
- `brief`: 2-3 个维度

### 4.3 商务评分

从行业模板 `scoring_defaults.business_scoring` 获取，按概要级别输出。

### 4.4 价格评分

从 `scoring.yaml` 获取价格评分公式选项，结合行业模板选择。

### 4.5 无效投标认定

从技术规格中的实质性要求（★标记项）提取 5-8 条核心条件。

### 4.6 交叉检查

- 每条实质性要求（技术规格中标为★的要求）都有对应评分项
- 控标点对应的要求已映射为评分项
- 技术评分总分符合行业模板权重

### 4.7 评标办法输出结构

```
一、评标方法
二、分值构成与权重
三、价格评分
四、商务评分细则（概要）
五、技术评分细则（详细，从技术规格自动映射）
六、无效投标认定
```

---

## Phase 5：DOCX 输出与交付

### 5.1 DOCX 生成（内容与渲染分离）

采用**内容与渲染分离**架构，避免在 Python 脚本中内嵌大量中文字符串导致 UTF-8 截断乱码：

**步骤一：生成 JSON 数据文件**

将 Phase 3-4 的全部文档内容组织为 JSON 结构，通过 Write 工具写入临时文件（如 `/tmp/tpl_content.json`）。JSON 格式见 `skills/twc/tools/tpl_docx_writer.py` 文件头部注释。

**步骤二：调用渲染工具**

```bash
python3 $SKILL_DIR/../twc/tools/tpl_docx_writer.py <content.json> <output.docx>
```

渲染工具会自动清理 JSON 中因 Write 传输产生的 U+FFFD 字符碎片，确保 DOCX 内容干净。

**步骤三：编码完整性校验**

```bash
python3 $SKILL_DIR/../twc/tools/docx_encoding_check.py --fix <output.docx> --max-retries 3
```

- `ENCODING_OK` 或 `FIX_OK` → 通过，继续交付
- `FIX_FAILED` → 3 次重试后仍有残留，通知用户人工修复：
  ```
  ⚠️ 文档存在无法自动清除的编码损坏（N 处），请人工检查以下位置：
  <工具输出的 UNFIXED 列表>
  建议：重新生成文档，或在 Word 中手动修正上述段落。
  ```

**文件命名**：
- 含评标办法：`技术规格与评标办法_<项目名>_<时间戳>.docx`
- 仅技术规格：`技术规格_<项目名>_<时间戳>.docx`

**文档结构**：
- 封面（标题、项目名、行业类型、生成日期）
- 目录占位（提示按 Ctrl+A → F9 更新）
- 第一部分：技术规格与要求（Phase 3 输出）
- 第二部分：评标办法（Phase 4 输出，若有）

### 5.2 反控标最终检查

生成 DOCX 前执行最终品牌名扫描，确保零残留。

### 5.3 文件交付

告知用户文件路径。

### 5.4 输出确认

```
技术规格[与评标办法]生成完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
文件名称：[文件名]
文件路径：[完整路径]
行业类型：[行业]
细致程度：[级别]
技术要求条目：X 条（含 Y 条控标点）
[评标办法维度：Z 个]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

反控标自检：✅ 通过

后续建议：
1. 打开 Word 文件，按 Ctrl+A → F9 更新目录
2. 审核技术要求的合理性和自然度
3. 建议通过 /trv --type tender_doc 进行深度审核
```

### 5.5 自动清理

若存在临时处理目录，自动删除。
