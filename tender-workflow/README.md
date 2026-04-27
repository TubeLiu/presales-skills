# Tender Workflow — AI 辅助招投标工作流

从招标文件到标书成稿的完整 AI 辅助解决方案。**四角色**（策划者 / 规划者 / 撰写者 / 审核者）覆盖招标、分析、撰写、审核全流程。

---

## 安装（Claude Code plugin）

`tender-workflow` 是 `presales-skills` umbrella marketplace 的成员 plugin：

```bash
/plugin marketplace add Alauda-io/presales-skills
/plugin install drawio@presales-skills
/plugin install ai-image@presales-skills
/plugin install anythingllm-mcp@presales-skills        # 可选；不装则降级为本地索引或联网
/plugin install tender-workflow@presales-skills
```

装完即可在任意目录调用 `/tpl` `/taa` `/taw` `/trv` `/twc` 五个命令。

源码模式（直接 `cd` 进本目录）也可工作，下文 `python skills/...` 命令在源码模式下直接执行。

---

## 四角色 + 数据流

| 角色 | Skill | 服务 | 任务 |
|---|---|---|---|
| 策划者 | `tpl` | 甲方 | 产品功能 → 招标技术规格 + 评标办法（无控标痕迹） |
| 规划者 | `taa` | 乙方 | 招标文件 → 7 模块分析报告 + 投标大纲 |
| 撰写者 | `taw` | 乙方 | 大纲 + KB → 章节草稿 DOCX |
| 审核者 | `trv` | 甲乙双方 | 多维度审核 + AI 智能修订 |

```
甲方：项目需求 → [tpl] → 招标文件 → [trv] → 发布
乙方：招标文件 → [taa] → 分析+大纲 → [trv] → [taw] → 章节草稿 → [trv] → 完整标书
```

---

## 用户输入路由（避免 5 个 skill 抢触发）

| 用户喊 | 视角 | 该用 |
|---|---|---|
| 写招标文件 / 生成招标技术规格 / 招标策划 / 反控标 | 甲方 | `/tpl` |
| 写标书 / 撰写章节 / 编写投标书 | 乙方 | `/taw`（**前置必须先 `/taa`**） |
| 分析招标文件 / 评估投标可行性 / 看看这份招标 | 乙方 | `/taa` |
| 审核招标文件本身的质量 / 检查招标文件 | 甲方 | `/trv --type tender_doc` |
| 审核投标分析 / 大纲 / 章节 / 完整标书 | 乙方 | `/trv --type analysis\|outline\|chapter\|full_bid` |
| 配置 / setup / show / validate / migrate / 配置不生效 | — | `/twc` |

歧义点（务必明确视角）：

- **"分析招标文件"** 默认乙方理解需求 → `/taa`；若用户其实想审甲方文件质量，用 `/trv --type tender_doc`
- **"写招标" vs "写标书"** 容易混淆——**招标** = 甲方 `/tpl`；**标书** = 乙方 `/taw`
- **`/taw` 永远要先跑 `/taa`**；直接喊 `/taw` 且无大纲会硬错（"报告不存在"）

---

## 常用命令

```bash
# 策划者
/tpl <功能清单> [--project <概述>] --template <government|finance|soe|enterprise> [--level detailed|standard|general|brief] [--no-scoring]

# 规划者
/taa <招标文件> [--product <产品能力.xlsx|.md>] [--vendor <厂商>] [--kb-source auto|anythingllm|local]

# 撰写者
/taw <目录> --chapter <章节号> [--vendor <厂商>] [--search-tool auto|websearch|<FQN>] [--image-source auto|local|drawio|ai|web|placeholder] [--image-provider ark|dashscope|gemini]

# 审核者
/trv <文件> --type <tender_doc|analysis|outline|chapter|full_bid> [--reference <参考>] [--revise-docx --revise-scope must|all]

# 配置
/twc setup       # 首次交互配置
/twc show        # 查看配置
/twc validate    # 健康检查
/twc models      # 列 AI 生图模型
```

详细参数：每个 skill 跑 `-h` / `--help`。

---

## taw 单章 vs 多章模式（重要）

`taw` 章节标题用 Word 原生**多级列表自动编号**（不在标题文本里写 "1.3.1 ..."）。

| 模式 | 命令 | Word 显示 | 用途 |
|---|---|---|---|
| **多章合并**（生产推荐） | `/taw <目录> --chapter all` 或范围 `1.1-1.11` | "1." 章 / "1.3" 节 / "1.3.1" 目 自然连续 | 正式投标 |
| 单章 standalone | `/taw <目录> --chapter 1.3` | 单文档自动从 "1." 起，不会显示 "1.3" | 仅本地预览 / 测试 |

单章模式不能保留原始章节号是 Word 多级列表设计的内禀属性（自动编号在单文档内从 1 起）。**正式投标必须用多章模式**让编号自然连续。

---

## 标书格式规范（2026 版）

`taw` 输出 DOCX 自动遵守：

- **页面**：A4，上下 2.5cm / 左右 2.4cm
- **标题**：H1 三号黑体加粗 / H2 小三宋体加粗 / H3 四号宋体加粗 / H4 13pt / H5 12pt（Word 多级列表自动编号 1, 1.1, 1.1.1, ...）
- **正文**：小四宋体 1.5 倍行距，首行缩进 2 字符
- **段距**：段前 / 段后 0.5 行
- **图片**：caption 在图下方，"图 X-Y 说明" 小五宋体居中
- **目录**：文档开头 TOC 域（Word 打开按 F9 更新）
- **过度承诺防范**：禁用 "保证" / "确保 100%" / "绝对" 等绝对化措辞，改用 "预期可达到 / 力争实现 / 设计目标为"
- **来源标注**：互联网具体数字标 `[互联网来源，请核实]`；无 KB 支撑标 `[待确认]`

---

## 知识库（Local-KnowledgeBase）

`taw` v3.0 用全 Markdown 图文一体化 KB：

```
<KB_ROOT>/
├── 技术方案-XXX/
│   ├── full.md            # 主文档（图片 ![](images/HASH.jpg) 内嵌）
│   ├── images/            # 图片目录
│   ├── content_list_v2.json
│   └── layout.json
└── .index/
    └── kb_catalog.yaml    # kb_indexer.py 自动生成
```

构建索引：

```bash
/taw --build-kb-index                                    # 用配置中的 localkb.path
/taw --build-kb-index --kb-path /path/to/Local-KnowledgeBase
```

KB 路径解析优先级：`--kb` 临时覆盖 > 配置 `localkb.path` > 首次运行引导。

---

## 配置

统一配置文件：`~/.config/tender-workflow/config.yaml`

```yaml
localkb:
  path: /data/Local-KnowledgeBase
anythingllm:
  workspace: <slug-or-uuid>          # 可选；用 anythingllm-mcp plugin 时填
ai_image:
  default_provider: ark              # ark / dashscope / gemini
```

解析优先级：**CLI 参数 > 环境变量 > skill 节 > 全局节 > 默认值**。

`/twc setup` 引导式 6 步配置（KB 路径 → AnythingLLM → draw.io → MCP 搜索工具 → skill 默认值 → 验证）。

### MCP 搜索工具

`/twc setup` §4 的 "MCP 搜索工具" 步骤分两半：

**半部分 a — 注册** （走 web-access plugin 的 `mcp_installer.py`，缺 `node`/`uv` 时 wizard 自动用户级安装；register 后会询问是否实测；**前置**：先装 `web-access` plugin，未装则跳过本步不影响其他配置）。三类内置候选：

| `<provider>` | Tool | 拿 key |
|---|---|---|
| `tavily` | `tavily_search` | https://tavily.com |
| `exa` | `web_search_exa` | https://exa.ai |
| `minimax`（MiniMax Token Plan） | `web_search` + `understand_image` | 订阅 [Token Plan](https://platform.minimaxi.com/subscribe/token-plan) 拿 `sk-cp-` 前缀 key（普通 chat key 不能给 MCP 用，见 [issue #96](https://github.com/MiniMax-AI/MiniMax-M2/issues/96)） |

**半部分 b — 选默认** （§4.4）：`mcp_installer.py list-search-tools` 会**实时枚举**当前 `~/.claude.json` 已注册的所有 MCP server（不止上面三类），让用户从真实可用的清单里挑默认搜索工具。新装的 MCP（不需要升级 plugin）下一次 setup 自动出现，符合 "Claude Code 里有什么就用什么" 的设计。

`mcp_search.priority` 存 FQN 列表（`mcp__<server>__<tool>` 或内置 `WebSearch`），工作流（taw / taa）按顺序试，全失败回 `WebSearch` 兜底。老 config 写的别名（`tavily_search` 等）由 `tw_config.py` 自动透明转 FQN。

---

## 子智能体架构（taw / 并行写作）

长章节（H3 ≥ 3 且目标字数 ≥ 4500）`taw` 自动启用并行写作：

```
Phase 2A 主 session 准备素材 + image_plan（KB / Web / AI 配图全部本地化）
   ↓
Phase 2B 并发分派 H3 writer subagent（Read agents/writer.md）
   ↓
Phase 2C 整合（拼接 + 引言 + 过渡 + 一致性 + M4 终检 + 图片清单核对）
   ↓
Phase 2.5R 并行分派 spec-reviewer + quality-reviewer subagent → 应用修订（最多 2 轮）
   ↓
Phase 3 输出 DOCX（多级列表 + TOC + 层级校验）
```

**零配置**：所有受限工具（Skill / mcp__* / WebSearch / WebFetch）由主 session 在 Phase 2A 一次性消费完毕；subagent 只用 Read / Bash / Glob / Grep 处理已准备好的素材。无需手动配置 `~/.claude/settings.json`。

---

## 故障排查

| 症状 | 处理 |
|---|---|
| `taw` 找不到大纲 / 报告 | 简写目录模式需目录里同时有 `.docx` + `.md`；或显式 `--outline` / `--report` 各传文件 |
| KB 检索 0 命中 | 跑 `/taw --build-kb-index` 重建索引；检查 `~/.config/tender-workflow/config.yaml` 里 `localkb.path` |
| AnythingLLM 调用失败 | 检查 `/plugin install anythingllm-mcp@presales-skills` 是否装过；或改用 `--kb-source local` 跳过 |
| draw.io 图表生成失败 | `/plugin install drawio@presales-skills`；CLI 备选要装 draw.io Desktop |
| AI 生图失败 | 跑 `/twc validate` 检查 API 配置；或改 `--image-source placeholder` |
| DOCX 标题层级错（1.3 显示成 H1） | 升级到 v2.0+（Word 多级列表自动编号）；不要在 heading text 里写编号 |
| 跨平台问题 | Windows 用 Git Bash / WSL2；路径用正斜杠 |

---

## 开发

```bash
# clone 后激活 pre-commit hook（自动跑 tests/test_skill_refs.py）
git config core.hooksPath tools/hooks

# 跑单元测试
python3 -m pytest -q

# 跑 SKILL.md 引用一致性检查
python3 -m pytest tests/test_skill_refs.py -v
```

详细架构 + skill 内部规范 → 见各 skill 的 `SKILL.md`：

- `skills/tpl/SKILL.md`、`skills/taa/SKILL.md`、`skills/taw/SKILL.md`、`skills/trv/SKILL.md`、`skills/twc/SKILL.md`
- `taw` 重型工作流细节按需 Read：`skills/taw/references/{cli-help, preflight, io-formats, templates, kb-retrieval, image-retrieval, markdown-writing}.md`
