# customer-research plugin — 多源客户调研

**中文** | [English](./README_EN.md)

对客户问题、产品主题或账户相关查询进行系统性多源调研，带来源归属和置信度评分。

适用于方案撰写前的客户画像准备、竞品分析、技术可行性验证、历史沟通回顾。

## Slash 入口

| 触发方式 | 形式 |
|---|---|
| Claude Code canonical | `/customer-research:research` |
| Codex / Cursor / OpenCode 短形式 alias | `/research` |
| 自然语言 auto-trigger | "调研客户" / "查一下 XX 公司背景" / "做一个客户调研" / "客户背景调查" / "行业调研" / "竞品调研" |

## 适用场景

- 接到客户名后快速出一份结构化背景画像
- 方案撰写前的知识准备（配合 `/solution-master:go` 使用）
- 竞品分析和技术可行性验证
- 历史沟通回顾（我们之前给这个客户报过什么？）
- 行业趋势和最佳实践调研

## 工作流（6 步）

1. **解析调研请求** — 识别调研类型（客户画像 / 问题调研 / 账户上下文 / 主题研究）
2. **搜索可用数据源** — 5 层分级搜索（内部文档 → 业务上下文 → 沟通记录 → 外网 → 推理类比）
3. **综合产出** — 结构化调研简报，含结论、关键发现、来源归属、置信度评分
4. **数据源不足处理** — 网络调研兜底 + 向用户询问内部上下文
5. **客户面向注意事项** — 标记敏感话题、建议免责声明、代拟回复
6. **知识沉淀** — 建议保存到知识库 / FAQ / runbook

## 产出示例

```
## 调研：XX 公司

### 结论
[清晰结论]

**置信度：** 高
[依据]

### 关键发现
**来自 [来源]：**
- [发现]

### 来源
1. [来源] — [贡献]

### 未确认 / 待补充
- [待确认项]

### 建议后续动作
- [行动项]
```

## 配置

首次执行时自动进入配置流程，或主动说"配置 customer-research"。

| 配置项 | 说明 | 配置文件 |
|---|---|---|
| `customer_research.user_company` | 用户所在企业（你自己的公司），调研时自动站在该企业视角分析 | `~/.config/presales-skills/config.yaml` |

```bash
# 查看配置
python3 <SKILL_DIR>/scripts/cr_config.py show

# 手动设置
python3 <SKILL_DIR>/scripts/cr_config.py set user_company "XX科技"

# 交互式配置
python3 <SKILL_DIR>/scripts/cr_config.py setup
```

## 与 solution-master 的关系

customer-research 负责**调研准备阶段**，solution-master 负责**方案撰写阶段**。典型工作流：

```
/customer-research "XX 公司智慧交通需求"   → 调研简报
/solution-master:go                         → 基于调研结果撰写方案
```

## 安装

**Claude Code：**

```
/plugin marketplace add TubeLiu/presales-skills
/plugin install customer-research@presales-skills
/reload-plugins
```

**其它 agent（Cursor / Codex / OpenCode 等）：**

```bash
npx skills add TubeLiu/presales-skills -a <agent>
```
