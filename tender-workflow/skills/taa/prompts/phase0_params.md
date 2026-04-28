# Phase 0 参数处理详细规则

本文件包含 taa skill 的完整参数解析规则、AnythingLLM 配置、产品能力索引加载策略。
由主编排器 SKILL.md 在 Phase 0.0 阶段按需读取。

---

## 使用方式

```bash
# 基本用法（使用默认索引或 AI 模糊评估）
/taa <招标文件路径>

# 指定产品能力说明书（精确评估匹配度）
/taa <招标文件路径> --product <产品能力说明书.xlsx|.md>

# 分析时保存索引到默认位置
/taa <招标文件路径> --product <产品能力说明书.xlsx> --save-index

# 指定厂商名称（必填，可在 /twc setup 配持久值）
/taa <招标文件路径> --vendor "博云"

# 组合使用
/taa <招标文件路径> --product specs/产品能力.md --vendor "博云"

# 仅构建产品能力索引（不执行分析）
/taa --build-index --product <产品能力说明书.xlsx>

# 从环境变量配置的默认文件构建索引
/taa --build-index

# 强制使用 AnythingLLM 作为产品能力来源（不可用则报错）
/taa <招标文件路径> --kb-source anythingllm

# 强制使用本地索引，跳过 AnythingLLM
/taa <招标文件路径> --kb-source local

# 指定 AnythingLLM workspace
/taa <招标文件路径> --anythingllm-workspace "产品能力库"

# 查看帮助信息
/taa -h
/taa --help
```

**参数说明**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `<招标文件>` | 位置参数 | 必选。招标文件路径（PDF/Word/图片） |
| `--product` | 文件路径 | 可选。产品能力说明书（Excel 或 Markdown），用于精确评估产品与招标要求的匹配度。**注意**：若同时使用 `--kb-source anythingllm`，此参数将被忽略（强制使用 AnythingLLM） |
| `--vendor` | 字符串 | 必填。厂商名称（可在 /twc setup 配持久值；缺失会报错引导）。影响角色定义、报告标题、支持度列名等 |
| `--build-index` | 标志 | 可选。仅构建产品能力索引并保存到默认位置，不执行分析。需配合 `--product` 或配置环境变量 `TAA_DEFAULT_PRODUCT` |
| `--save-index` | 标志 | 可选。分析时将索引保存到默认位置（需配合 `--product` 使用） |
| `--anythingllm-workspace` | 字符串 | 可选。指定 AnythingLLM workspace slug 或名称。未指定时使用配置文件，否则自动取第一个 workspace |
| `--kb-source` | 字符串 | 可选。产品能力来源控制：`auto`（默认，先 AnythingLLM 后本地索引）、`anythingllm`（强制使用 AnythingLLM，不可用则报错） |

**环境变量**：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `TAA_DEFAULT_PRODUCT` | 默认产品能力文件路径，用于 `--build-index` 无参数时 | `/data/products/ACP_4.2.0.xlsx` |
| `TAA_ANYTHINGLLM_WS` | 默认 AnythingLLM workspace，优先级低于配置文件和命令行参数 | `product-kb` |

**配置文件**：`~/.config/tender-workflow/config.yaml`（统一配置，通过 `/twc setup` 管理）
```yaml
anythingllm:
  workspace: product-kb              # 全局默认 AnythingLLM workspace
taa:
  anythingllm_workspace: null        # taa 专属覆盖（null = 用全局值）
```

**参数组合规则**：

| 组合 | 行为 |
|------|------|
| `--build-index` + `--product` | 从指定文件构建索引并保存，退出 |
| `--build-index` 单独使用 | 从环境变量 `TAA_DEFAULT_PRODUCT` 构建索引，退出 |
| `--save-index` + `--product` + 招标文件 | 分析并保存索引到默认位置 |
| `--product` + 招标文件 | 分析但不保存索引（临时索引） |
| `--kb-source anythingllm` + `--product` | **冲突**：`--kb-source anythingllm` 优先，忽略 `--product` 文件 |
| `--kb-source local` + 招标文件 | 强制使用本地索引，跳过 AnythingLLM 检测 |
| 仅招标文件 | 使用默认索引（若存在）或 AI 模糊评估 |

**产品能力说明书格式**：

支持 Markdown（`.md`）或 Excel（`.xlsx`）格式，需包含以下信息：

- **技术能力**：按分类列出产品功能及技术参数（如最大节点数、支持的架构等）
- **国产化适配**：已适配的芯片/OS/数据库/中间件型号
- **资质证书**：企业资质、产品认证（如 CMMI、等保、信创目录等）
- **案例业绩**：行业、规模、交付时间等关键信息
- **服务能力**：运维体系、SLA 承诺、服务网络等


---

### 0.0 参数解析

**帮助参数检测**：

若用户指令中含有 `-h`、`--help` 或 `help`（忽略其他参数），立即输出以下帮助文本并退出（不执行后续任何步骤）：

```
─────────────────────────────────────────────────────
招标分析助手（taa）— 命令参数帮助
─────────────────────────────────────────────────────

用法：
  /taa <招标文件路径> [选项...]
  /taa --build-index --product <产品能力说明书>
  /taa -h | --help

参数：
  <招标文件路径>        必选。招标文件路径（PDF/Word/图片）
  --product <文件>      可选。产品能力说明书（Excel/Markdown），用于精确评估
  --vendor <名称>       必填。厂商名称（可在 /twc setup 配持久值）
  --build-index         可选。仅构建索引并保存，不执行分析
  --save-index          可选。分析时保存索引到默认位置
  --anythingllm-workspace <名称>  可选。指定 AnythingLLM workspace
  --kb-source <来源>    可选。产品能力来源控制：
                          auto（默认）：先 AnythingLLM，后本地索引
                          anythingllm：强制使用 AnythingLLM（不可用则报错）
                          local：强制使用本地索引，跳过 AnythingLLM

示例：
  /taa 招标文件.pdf
  /taa 招标文件.pdf --product 产品能力.xlsx
  /taa 招标文件.pdf --kb-source anythingllm
  /taa 招标文件.pdf --kb-source local
  /taa 招标文件.pdf --anythingllm-workspace "产品能力库"
  /taa --build-index --product 产品能力.xlsx
─────────────────────────────────────────────────────
```

从用户指令中解析以下参数（`-h`/`--help` 除外）：

1. **`--vendor`**：若用户提供 `--vendor "厂商名"` → `VENDOR_NAME = 用户提供的厂商名`；否则 → 读 `taa.vendor` config（`python3 $TW_DIR/skills/twc/tools/tw_config.py get taa.vendor`），仍为空 → **报错并引导用户**：`vendor 未配置。请运行 /twc setup 或 tw_config.py set taa.vendor <你的厂商名>，或在命令行加 --vendor`
2. **`--product`**：产品能力说明书路径（见下方解析规则）
3. **`--build-index`**：仅构建索引标志
4. **`--save-index`**：保存索引标志
5. **`--anythingllm-workspace`**：AnythingLLM workspace slug 或名称（可选）
6. **`--kb-source`**：产品能力来源控制（可选，默认 `auto`）

**参数处理流程**：

```
┌─────────────────────────────────────────────────────────────┐
│ Step 0: 解析 --kb-source 参数                                │
│   - 若用户提供 --kb-source anythingllm → KB_SOURCE_OVERRIDE  │
│     = "anythingllm"（强制使用 AnythingLLM）                   │
│   - 否则 → KB_SOURCE_OVERRIDE = "auto"（默认）               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 0.5: 解析 --anythingllm-workspace 参数                   │
│   - 若用户提供 --anythingllm-workspace "名称" →               │
│     ANYTHINGLLM_WS_OVERRIDE = "名称"                          │
│   - 否则 → ANYTHINGLLM_WS_OVERRIDE = null                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 检测 --build-index 标志                              │
│   若存在 → 执行索引构建流程（见下方），完成后退出              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 1.5: AnythingLLM 可用性检测（根据 --kb-source 调整）     │
│                                                              │
│   执行检测：                                             │
│   1. 尝试调用 anythingllm_search（query="test"）：            │
│      - 成功 → 继续步骤 2                                     │
│      - 失败 → ANYTHINGLLM_AVAILABLE=false                    │
│         若 KB_SOURCE_OVERRIDE = "anythingllm" → 报错退出      │
│                                                              │
│   2. 调用 anythingllm_list_workspaces 获取所有 workspace 列表  │
│                                                              │
│   3. 确定目标 workspace（优先级从高到低）：                    │
│      a) --anythingllm-workspace 参数值                        │
│         → 在列表中按 slug 或 name 匹配                          │
│      b) ~/.config/tender-workflow/config.yaml 中的             │
│         taa.anythingllm_workspace 或 anythingllm.workspace    │
│         → 同上匹配                                            │
│      c) 环境变量 TAA_ANYTHINGLLM_WS                           │
│         → 直接使用                                            │
│      d) 以上均无 → 取列表中第一个 workspace                    │
│                                                              │
│   4. 记录结果：                                               │
│      - ANYTHINGLLM_AVAILABLE=true                            │
│      - ANYTHINGLLM_WS=<slug>（用于后续查询调用）              │
│      - ANYTHINGLLM_WS_NAME=<name>（用于日志显示）             │
│                                                              │
│   5. 输出检测日志：                                           │
│      "AnythingLLM 可用，workspace: <name> (<slug>)"           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 解析产品能力来源（根据 --kb-source 调整）             │
│                                                              │
│   若 --product 提供 且 KB_SOURCE_OVERRIDE != "anythingllm"： │
│      → 解析指定文件 → PRODUCT_INDEX（最高优先，精确评估）     │
│                                                              │
│   否则若 KB_SOURCE_OVERRIDE = "anythingllm"：                │
│      - ANYTHINGLLM_AVAILABLE=true → PRODUCT_SOURCE=anythingl │
│      - ANYTHINGLLM_AVAILABLE=false → 已报错退出（见 Step1.5）│
│                                                              │
│   否则若 KB_SOURCE_OVERRIDE = "auto"（默认）：               │
│      - ANYTHINGLLM_AVAILABLE=true → PRODUCT_SOURCE=anythingl │
│      - 否则检测本地索引版本：                                 │
│         - 若 .index/product_l0.yaml 存在 → V2 三层             │
│         - 否则若 .index/product.yaml 存在 → V1 单             │
│         - 否则 → PRODUCT_INDEX = null（AI 模糊评估）          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 检测 --save-index 标志                               │
│   若存在且有 PRODUCT_INDEX → 保存到 .index/product.yaml        │
└─────────────────────────────────────────────────────────────┘
```

**索引构建流程（--build-index）**：

```
1. 确定源文件：
   - 若有 --product 参数 → 使用指定文件
   - 否则检查环境变量 TAA_DEFAULT_PRODUCT → 使用配置路径
   - 否则 → 报错退出："未指定产品能力文件，请使用 --product 或配置 TAA_DEFAULT_PRODUCT 环境变量"

2. 解析文件（见下方产品能力文件解析规则）

3. 保存索引：
   - V2 模式：生成三层索引文件
     ```bash
     python3 .claude/skills/taa/tools/indexer_v2.py --input [临时解析文件] --output .index/
     # 或使用 --output 指定输出目录
     python3 .claude/skills/taa/tools/indexer_v2.py --input [文件] --output /path/to/output/.index/
     ```
   - V1 模式（兼容）：保存到 .index/product.yaml

4. 输出构建结果摘要：
   ```
   索引构建完成（V2 三层索引）：
   • 源文件：[文件路径]
   • 生成时间：[时间戳]
   • 功能条目：472 条
   • 分类数：11 个
   • 存储位置：.index/product_l*.yaml
   • Token 节省：~70-90%（vs V1 单文件）
   ```

5. 退出（不执行后续分析）
```

**默认索引加载（V2 三层索引）**：

当 `--product` 未提供时，按以下优先级检测索引：

```bash
# 优先检测 V2 三层索引
if [ -f ".index/product_l0.yaml" ]; then
    echo "发现 V2 三层索引"
    INDEX_VERSION="V2"
# 兜底检测 V1 单文件索引（向后兼容）
elif [ -f ".index/product.yaml" ]; then
    echo "发现 V1 单文件索引"
    INDEX_VERSION="V1"
else
    echo "未发现产品能力索引"
    INDEX_VERSION="NONE"
fi
```

**V2 三层索引加载策略**：

1. **初始化阶段（Step 2）**：
   - 只加载 L0 快速路由索引（~2KB）
   - 读取 11 个分类的概览信息
   - 输出提示：
     ```
     使用 V2 三层索引（11 个分类，共 472 条条目）
     • L0 已加载：2KB
     • L1/L2 将按需加载（节省 ~147KB）
     ```

2. **M4 技术要求评估阶段**：
   - 提取招标文件技术要求章节的核心关键词
   - 匹配 L0 中的分类（根据 core_keywords）
   - 加载匹配分类的 L1 文件（1-3 个，总计 5-30KB）
   - 输出加载摘要：
     ```
     已加载分类：
     • Container Management (126条, 19KB)
     • DevOps & CI/CD (59条, 9.4KB)
     总计：28.4KB（vs V1 149KB，节省 81%）
     ```

3. **详细参数查询（按需）**：
   - 仅在评分标准要求具体参数时，加载对应 L2 文件

**V1 单文件索引（向后兼容）**：

若存在，读取该文件作为 `PRODUCT_INDEX`，并输出提示：
```
使用 V1 单文件索引（[N] 条条目，构建于 [日期]）
```

若不存在：
```
未提供产品能力说明书，将使用 AI 模糊评估
```

**产品能力文件解析规则**：

- **Markdown 文件**（`.md`）：直接读取全文内容作为产品能力上下文
- **Excel 文件**（`.xlsx`）：使用 Bash 执行 Python 脚本生成**结构化产品能力索引**：

  ```bash
  python3 << 'PYTHON_SCRIPT'
  import openpyxl, yaml, sys, re
  from datetime import datetime

  def extract_keywords(entry):
      """从条目提取搜索关键词"""
      keywords = set()
      text = f"{entry.get('name','')} {entry.get('description','')} {entry.get('parameters','')}"
      words = re.findall(r'[a-zA-Z]+|[\u4e00-\u9fa5]+', text)
      for w in words:
          if len(w) > 2:
              keywords.add(w.lower() if w.isascii() else w)
      return list(keywords)[:10]

  def parse_product_excel(filepath):
      wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
      product_index = {
          'source_file': filepath,
          'generated_at': datetime.now().isoformat(),
          'total_entries': 0,
          'sheets': []
      }

      for ws in wb.worksheets:
          sheet_data = {'name': ws.title, 'headers': [], 'entries': []}
          rows = list(ws.iter_rows(values_only=True))
          if len(rows) < 2:
              continue

          sheet_data['headers'] = [str(c) if c else '' for c in rows[0]]

          # 识别关键列
          headers_lower = [h.lower() for h in sheet_data['headers']]
          col_map = {}
          for i, h in enumerate(headers_lower):
              if any(k in h for k in ['分类', '类别', '类型']):
                  col_map['category'] = i
              elif any(k in h for k in ['功能', '名称', '功能点', '能力项']):
                  col_map['name'] = i
              elif any(k in h for k in ['描述', '说明']):
                  col_map['description'] = i
              elif any(k in h for k in ['参数', '指标', '规格']):
                  col_map['parameters'] = i

          # 提取条目
          current_category = '未分类'
          for idx, row in enumerate(rows[1:], 1):
              cells = [str(c) if c is not None else '' for c in row]
              if not any(cells):
                  continue

              if 'category' in col_map and cells[col_map['category']].strip():
                  current_category = cells[col_map['category']].strip()

              entry = {
                  'id': f"{ws.title}_{idx}",
                  'category': current_category,
                  'name': cells[col_map.get('name', 0)] if col_map.get('name', 0) < len(cells) else '',
                  'description': cells[col_map.get('description', 1)] if col_map.get('description', 1) < len(cells) else '',
                  'parameters': cells[col_map.get('parameters', 2)] if col_map.get('parameters', 2) < len(cells) else '',
              }
              entry['keywords'] = extract_keywords(entry)
              sheet_data['entries'].append(entry)

          product_index['sheets'].append(sheet_data)
          product_index['total_entries'] += len(sheet_data['entries'])

      return product_index

  if __name__ == '__main__':
      index = parse_product_excel(sys.argv[1])
      print(yaml.dump(index, allow_unicode=True, default_flow_style=False, sort_keys=False))
  PYTHON_SCRIPT
  ```

  将输出的 YAML 索引作为 **PRODUCT_INDEX**，用于后续 M2 技术匹配。

  **错误处理**：
  - 如果 Excel 文件格式不符合预期（无法识别关键列）→ 输出警告，降级到"无产品能力说明书"模式（AI 模糊评估）
  - 如果 Python 脚本执行失败（缺少依赖、文件损坏等）→ 输出错误信息，降级到"无产品能力说明书"模式
  - 降级时在报告中说明：`⚠️ 产品能力文件解析失败，使用 AI 模糊评估模式`

  **PRODUCT_INDEX 结构说明**：
  ```yaml
  source_file: "产品能力说明书.xlsx"
  generated_at: "2026-03-07T10:00:00"
  total_entries: 150
  sheets:
    - name: "技术能力清单"
      headers: ["功能分类", "功能名称", "功能描述", "技术参数"]
      entries:
        - id: "技术能力清单_1"
          category: "平台管理"
          name: "多集群管理"
          description: "支持同时管理多个Kubernetes集群..."
          parameters: "最大支持100个集群"
          keywords: ["多集群", "集群管理", "K8s", "Kubernetes"]
    - name: "资质证书"  # 可选，用于 M3 商务要求分析
      entries:
        - id: "资质证书_1"
          category: "企业资质"
          name: "CMMI 5级"
          description: "软件能力成熟度模型集成5级认证"
    - name: "案例业绩"  # 可选，用于 M3/M4 分析
      entries:
        - id: "案例业绩_1"
          category: "金融行业"
          name: "某银行容器云平台"
          description: "2023年交付，规模1000+节点"
  ```

  **说明**：
  - 技术能力清单为必选，用于 M2 技术匹配
  - 资质证书和案例业绩为可选，如果产品能力文件中包含这些信息，解析脚本会自动提取
  - 如果缺少资质或案例信息，M3/M4 分析时使用 AI 模糊评估

解析完成后宣告：

```
参数解析：
• 厂商名称：{VENDOR_NAME}
• 产品能力索引：[来源类型] ✅ 已加载（[N] 条功能条目，[M] 个分类）
```

**来源类型**：
- `--product 指定文件`：用户通过 `--product` 参数指定
- `默认索引`：从 `.index/product.yaml` 加载
- `临时解析`：从 `--product` 指定文件临时解析
- `无索引`：未提供且无默认索引，将使用 AI 模糊评估

**变量替换机制**：

在后续 Phase 1 和 Phase 2 中，需要将 `VENDOR_NAME` 替换到所有 prompt 文件中的 `{VENDOR_NAME}` 占位符：

1. **Phase 1 开始前**：读取 `prompts/analysis.yaml` 和行业模板文件，将其中所有 `{VENDOR_NAME}` 替换为实际的厂商名
2. **Phase 2 开始前**：读取 `prompts/outline.yaml`，将其中所有 `{VENDOR_NAME}` 替换为实际的厂商名
3. **替换方式**：在内存中完成替换，不修改原始文件

示例：若 `VENDOR_NAME = "博云"`，则：
- `{VENDOR_NAME}售前投标专家` → `博云售前投标专家`
- `{VENDOR_NAME}支持度` → `博云支持度`

