# Phase 0：参数解析与输入加载详解

> **何时读本文件**：用户首次调用 `/tpl` 时，或对 `--template` / `--level` / `--no-scoring` 等参数语义不确定时。
>
> 简单调用（已知参数完整）不需要读，按 SKILL.md §Phase 0 概要执行即可。

## 目录

1. 0.0 参数解析（含 --help 输出、参数验证规则、行业映射）
2. 0.05 配置加载（可选，从 ~/.config/tender-workflow/config.yaml 读默认值）

---

## 1. Phase 0.0 参数解析

### 步骤一：检测帮助参数

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

### 步骤二：解析参数

从用户指令中解析以下参数：

1. **产品功能清单**（位置参数，必选 —— 除非使用 `--kb`）
2. **`--kb`**（可选）：使用知识库产品索引
3. **`--project`**（可选）：项目概述文件
4. **`--template`**（必选）：行业类型
5. **`--level`**（可选，默认 `standard`）：细致程度
6. **`--no-scoring`**（可选）：跳过评标办法

### 步骤三：参数验证

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

### 步骤四：参数解析完成宣告

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

---

## 2. Phase 0.05 配置加载（可选）

读取统一配置文件获取默认值（可被命令行参数覆盖）：

```bash
python3 $SKILL_DIR/../twc/tools/tw_config.py get tpl default_template
python3 $SKILL_DIR/../twc/tools/tw_config.py get tpl default_level
```

- 若未指定 `--template` 且配置中 `tpl.default_template` 有值 → 使用配置值作为默认模板
- 若未指定 `--level` 且配置中 `tpl.default_level` 有值 → 使用配置值作为默认级别
- 配置文件：`~/.config/tender-workflow/config.yaml`，通过 `/twc setup` 管理
