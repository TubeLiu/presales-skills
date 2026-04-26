# taw 文件加载 + 验证规则

主 SKILL.md §Phase 0 列了"加载大纲 + 报告 + 检测 KB"三大任务；本文件给细节。

## 1. 大纲（.docx）解析

`OUTLINE_PATH` 用 `python-docx` 读取，按 Heading 样式提取层级 + 文本：

```bash
python3 -c "import docx" 2>/dev/null || python3 -m pip install python-docx -q --break-system-packages 2>/dev/null
python3 -c "
from docx import Document
import sys
doc = Document(sys.argv[1])
for para in doc.paragraphs:
    level = ''
    if para.style.name.startswith('Heading'):
        try:
            level = '#' * int(para.style.name.split()[-1]) + ' '
        except ValueError:
            pass
    if para.text.strip():
        print(f'{level}{para.text}')
" "$OUTLINE_PATH"
```

提取：
- 章节编号 + 标题 → 一/二/三级目录树
- 目标章节内容 → 定位用户 `--chapter` 指定章节段落
- 子节列表 → `OUTLINE_SUBSECTIONS[章节号] = [{numbering, title, depth}, ...]`（最深 depth=5）

## 2. 招标分析报告（.md）

直接 Read。模块标题模式：

| 模块 | 标题匹配 | 用途 |
|---|---|---|
| M1 | `## M1` 或 `## 一、基础信息` | 项目背景 |
| M2 | `## M2` 或 `## 二、技术要求` | 技术要求矩阵 |
| M3 | `## M3` 或 `## 三、商务要求` | 商务条款 |
| M4 | `## M4` 或 `## 四、评分标准` | 评分细则 |
| M5 | `## M5` 或 `## 五、废标条款` | 红线条款 |
| M7 | `## M7` 或 `## 七、投标策略` | 撰写指导 |

每模块从其标题行起，到下一个同级 `##` 止。Grep 定位行号 → Read 范围。

## 3. KB 检测

若 `NO_KB_FLAG=true` → 跳过本节，所有 KB 标记为空。

否则：

```
KB_CATALOG = null
KB_ROOT = python3 $SKILL_DIR/../twc/tools/tw_config.py get taw localkb.path
if KB_ROOT/.index/kb_catalog.yaml exists:
  KB_CATALOG = Read(KB_ROOT/.index/kb_catalog.yaml)
  log: "[KB] 已加载目录索引: {len(entries)} 个文档"
else:
  log: "⚠️ KB 目录索引未建立，建议运行 /taw --build-kb-index"
```

KB 图片路径（v3.0 Local-KnowledgeBase 格式）：`{KB_ROOT}/{dir}/images/{hash}.jpg`

## 4. 输入验证（Phase 0.3）

输出（每项必含）：

```
已加载文件：
1. 大纲：[OUTLINE_PATH 实际文件名] - 章节数：[N]
2. 报告：[REPORT_PATH 实际文件名] - 模块：M1-M7 [+ 行业扩展 E1-E3]
3. 知识库状态：
   - 来源配置：--kb-source = [auto/local/anythingllm/none]
   - AnythingLLM：✅ 可用（workspace: [name]）/ ⚠️ 不可用
   - KB 目录索引：✅ 已加载 [N 个文档] / ⚠️ 未建立
4. 搜索工具：
   - MCP 可用：tavily_search / exa_search ✅ 或 ⚠️ 仅 WebSearch
   - 优先级：WebSearch → tavily → exa
5. 图片来源：--image-source = [auto/local/drawio/ai/web/placeholder]

目标章节：[章节号] [章节名]
```

若 `OUTLINE_PATH` 或 `REPORT_PATH` 是经目录匹配得出，追加：

```
（目录自动匹配：[目录] → [实际文件名]，如需指定其他文件请使用完整路径）
```

报告不存在或解析失败 → 提示用户先跑 `/taa`。

## 5. 启动确认（Phase 0.4，无需用户回复）

```
─────────────────────────────────────
撰写启动：
• 大纲文件：[OUTLINE_PATH 文件名]
• 分析报告：[REPORT_PATH 文件名]
• 目标章节：[原始输入] → 展开为 [N] 个章节：[1.1, 1.2, ...]
• 知识库：[状态]
• 输出目录：./drafts/
─────────────────────────────────────
```

单节模式下"目标章节"行直接显示编号 + 名称，不展开。
