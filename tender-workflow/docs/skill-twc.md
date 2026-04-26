# TWC — Tender Workflow 配置管理 技术文档

> 版本：v1.0 | 角色：配置管理者 | 服务对象：所有角色（taa/taw/tpl/trv）

---

## 1. 设计目标

TWC 是 Tender Workflow 四角色系统的**统一配置中枢**，负责管理所有 Skill 共享的运行时配置。核心设计目标：

1. **单一配置源**：所有 Skill 从同一个 YAML 文件读取配置，消除配置散落问题
2. **层级覆盖**：支持全局默认值 + Skill 专属覆盖 + 命令行参数三级优先级
3. **零手动编辑**：通过交互式向导和 CLI 命令完成所有配置操作

---

## 2. 配置架构

### 2.1 唯一配置文件

路径：`~/.config/tender-workflow/config.yaml`

历史上 taa 和 taw 各自维护独立的配置文件（`~/.config/taa/config.yaml` 和 `~/.config/taw/config.yaml`），现已废弃并统一。

### 2.2 配置 Schema 结构

```yaml
# ─── 全局共享（所有 Skill 可读取）───
localkb:
  path: /path/to/Local-KnowledgeBase              # 知识库根目录

anythingllm:
  enabled: true/false                  # 是否启用 AnythingLLM
  base_url: "http://localhost:3001"    # AnythingLLM 服务地址
  workspace: <slug-or-uuid>           # 全局默认 workspace

api_keys:
  ark: <火山方舟 API Key>              # Seedream 生图
  dashscope: <阿里云 API Key>          # 通义万相生图
  gemini: <Google Gemini API Key>      # Gemini 多模态生图

ai_image:
  default_provider: ark                        # 默认供应商（ark/dashscope/gemini）
  size: 2048x2048
  max_retries: 2
  timeout: 60
  models:
    ark: doubao-seedream-5-0-260128
    dashscope: qwen-image-2.0-pro
    gemini: gemini-2.5-flash-image

mcp_search:
  priority: [tavily_search, exa_search]  # MCP 搜索工具优先级

drawio:
  cli_path: /Applications/draw.io.app/Contents/MacOS/draw.io

# ─── Skill 专属覆盖（仅对应 Skill 读取）───
taa:
  vendor: 灵雀云
  kb_source: auto
  anythingllm_workspace: null          # null = 用全局值

taw:
  kb_source: auto
  image_source: auto
  anythingllm_workspace: null

tpl:
  default_template: null
  default_level: standard

trv:
  default_level: all
```

### 2.3 配置解析优先级（五级）

```
CLI 参数 > 环境变量 > 统一配置(skill 节) > 统一配置(全局节) > 默认值
```

**示例**：taw 需要 AnythingLLM workspace 时：
1. `--anythingllm-workspace "my-ws"` → 使用 `my-ws`
2. 环境变量 `TAW_ANYTHINGLLM_WS` → 使用该值
3. `config.yaml` 中的 `taw.anythingllm_workspace` → 使用该值
4. `config.yaml` 中的 `anythingllm.workspace` → 使用全局值
5. 以上均无 → 自动检测第一个可用 workspace

---

## 3. 工具实现

### 3.1 tw_config.py

位于 `skills/twc/tools/tw_config.py`，是配置读写的唯一后端工具，同时支持 CLI 调用和 Python import。

```bash
# CLI 调用方式
python3 skills/twc/tools/tw_config.py show [skill]          # 显示配置
python3 skills/twc/tools/tw_config.py get <skill> <key>     # 获取单个值（支持 dot notation）
python3 skills/twc/tools/tw_config.py set <key> <value>     # 设置值
python3 skills/twc/tools/tw_config.py models [provider]     # 列出 AI 生图模型
python3 skills/twc/tools/tw_config.py validate              # 健康检查
python3 skills/twc/tools/tw_config.py migrate               # 迁移旧配置
python3 skills/twc/tools/tw_config.py normalize             # 规范化 schema
```

所有 Skill 的 SKILL.md 中需要读取配置时，统一通过此工具：
```bash
python3 skills/twc/tools/tw_config.py get taw localkb.path
```

---

## 4. 子命令工作流程

### 4.1 `/twc setup`（交互式配置向导）

分 6 步引导用户完成完整配置，每步完成后立即写入配置文件：

| 步骤 | 配置项 | 检测逻辑 |
|------|--------|----------|
| Step 1 | 知识库路径 | `git rev-parse --show-toplevel` 检测项目根目录，查找 `Local-KnowledgeBase/` |
| Step 2 | AnythingLLM | 检查 `which mcp-anythingllm`，测试连通性，选择 workspace |
| Step 3 | draw.io | 检查 Skill 安装 + CLI 路径检测（macOS/Windows/Linux） |
| Step 4 | AI 生图 API Key | 检测环境变量 `ARK_API_KEY`/`DASHSCOPE_API_KEY`/`GEMINI_API_KEY` |
| Step 5 | Skill 默认值 | 设置 taa 厂商名、tpl 默认模板和级别 |
| Step 6 | 验证与迁移 | 执行 `validate`，检查旧配置文件并提供迁移选项 |

### 4.2 `/twc models [provider]`

**数据来源**：`skills/taw/prompts/ai_image_models.yaml`（模型注册表）

工作流程：
1. 调用 `tw_config.py models [provider]` 生成 Markdown 表格
2. 表格中标记当前配置的默认模型（`←` 箭头）
3. 区分 `★ 推荐`（注册表静态属性）和 `● 当前默认`（用户配置 `ai_image.models.*`）
4. 若 `last_updated` 距今超过 90 天，自动显示过期警告

### 4.3 `/twc validate`

健康检查项：
- 配置文件语法正确性
- 知识库路径存在性
- API Key 格式校验
- AnythingLLM 连通性
- draw.io CLI 可用性

### 4.4 `/twc migrate`

迁移旧的 per-skill 配置：
1. 检查 `~/.config/taw/config.yaml` 和 `~/.config/taa/config.yaml`
2. 将旧配置键值映射到新 schema
3. 合并到统一配置文件
4. 删除旧配置文件

---

## 5. 与其他 Skill 的集成

TWC 不直接参与招投标业务流程，而是作为配置基础设施被所有 Skill 消费：

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│   tpl   │     │   taa   │     │   taw   │     │   trv   │
└────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘
     │               │               │               │
     └───────────────┴───────────────┴───────────────┘
                           │
                    ┌──────┴──────┐
                    │  tw_config  │  ← Python 工具
                    └──────┬──────┘
                           │
                ┌──────────┴──────────┐
                │  config.yaml (唯一)  │
                └─────────────────────┘
```

每个 Skill 在 Phase 0 阶段调用 `tw_config.py get <skill> <key>` 获取配置值，CLI 参数优先级最高可覆盖配置文件中的值。
