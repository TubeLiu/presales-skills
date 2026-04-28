# 配置详解

本文件覆盖：4 个 setup wizard 的范围、配置文件物理布局、纯 CLI 配置、自动依赖安装与跳过开关。

> 90% 的用户场景**直接对 AI 说自然语言**即可配置——不需要读本文件。本文件给 power user 与维护者参考。

---

## 1. 4 个 setup wizard 总览

每个 plugin 的"配置"和"使用"都直接对 AI 说自然语言即可。所有 wizard **一步问、立即写入、立即验证**；任何"可选"字段都允许跳过。

| 你说什么 | 对应 wizard |
|---|---|
| `配置 ai-image` / `首次配置` | API keys（13 provider 任一）→ 默认 provider → 默认尺寸 → validate |
| `配置 web-access` / `启用 CDP` | Node.js 22+ → Chrome remote debugging → CDP Proxy 启动验证 → 风险告知 |
| `配置 solution-master` | localkb → AnythingLLM（可选）→ MCP 搜索注册（tavily/exa/minimax）→ **动态枚举所有已装 MCP 让你选默认** → CDP 登录态站点（可选）→ draw.io 检测 |
| `配置 tender` / `配置工作流` | 6 步 tender 专属配置（localkb / anythingllm / drawio / mcp_search 注册 + 选默认 / skill 默认值） |

**其它 plugin 不需要专属配置**：

- `ppt-master` 复用 ai-image API keys
- `drawio` 运行时自动检测桌面版 CLI
- `anythingllm-mcp` 装上自动注册 MCP server
- `skill-optimizer` 装上即用

---

## 2. 配置文件物理布局

| 文件 | 字段 | 由哪个工具管 |
|---|---|---|
| `~/.config/presales-skills/config.yaml` | `api_keys` / `ai_image` / `ppt_master.default_layout`（共享） | ai-image 的 `ai_image_config.py` |
| `~/.config/solution-master/config.yaml` | `localkb` / `anythingllm` / `cdp_sites` / `drawio` / `mcp_search` | solution-master 的 `sm_config.py` |
| `~/.config/tender-workflow/config.yaml` | tender 专属字段 | tender-workflow 的 `tw_config.py` |
| `~/.claude.json` 顶层 `mcpServers` | tavily / exa / minimax / anythingllm 等 MCP server 注册 | web-access 的 `mcp_installer.py`（搜索类）/ anythingllm-mcp `plugin.json`（自动） |

**为什么不合并**：sm 与 tw 是两个独立工作流，各自的配置语义不重叠（sm 的 `cdp_sites` / tw 的 `vendor_name`）；硬合到一个文件反而模糊职责。共享的部分（API keys / ai_image / ppt 默认模板）放在 `presales-skills/config.yaml` 已经收敛。

---

## 3. 纯 CLI 配置（不走 Claude）

```bash
# ai-image 共享配置（含 auto-migrate 旧 plugin 配置）
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" setup
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" set api_keys.ark <key>
python3 "$AI_IMAGE_DIR/scripts/ai_image_config.py" validate

# solution-master 专属配置
python3 "$SM_DIR/scripts/sm_config.py" set localkb.path <path>
python3 "$SM_DIR/scripts/sm_config.py" validate

# tender-workflow 专属配置
python3 "$TW_DIR/skills/twc/tools/tw_config.py" set localkb.path <path>
python3 "$TW_DIR/skills/twc/tools/tw_config.py" validate

# web-access 注册 web 搜索 MCP server
python3 "$WA_DIR/skills/browse/scripts/mcp_installer.py" check uv
python3 "$WA_DIR/skills/browse/scripts/mcp_installer.py" register minimax --key=sk-cp-xxxx
python3 "$WA_DIR/skills/browse/scripts/mcp_installer.py" test minimax
```

`$AI_IMAGE_DIR` / `$SM_DIR` / `$TW_DIR` / `$WA_DIR` 是跨 plugin 调用的占位符 —— 各 plugin 自家 SKILL.md 顶部的 §路径自定位 段只设 `$SKILL_DIR`（指本 plugin），跨 plugin 用法请复用 [`ai-image/skills/gen/SKILL.md`](../ai-image/skills/gen/SKILL.md) 中"建议跨 plugin 复用"段的 bootstrap heredoc 模板，仅替换其中的 plugin 名（`/ai-image/` → `/tender-workflow/` 等）和输出变量名。完整路径解析约定见 [docs/architecture.md §3](architecture.md#3-跨-plugin-调用约定)。

---

## 4. 自动依赖安装

所有 Python 依赖由入口脚本首次调用时自动 `pip install`：每个脚本开头调 `_ensure_deps.py`，检查 `<skill>/.deps-installed` marker，不存在则装。

**版本失效自动重装**：plugin 升级时 cache 路径带版本号，marker 不跨版本继承，自动触发新依赖重装。

### 跳过自动安装（CI / 容器 / 自管 venv）

```bash
export PRESALES_SKILLS_SKIP_AUTO_INSTALL=1
```

设了这个环境变量后必须自己装依赖：

```bash
pip install -r ~/.claude/plugins/cache/presales-skills/ppt-master/*/skills/make/requirements.txt
pip install -r ~/.claude/plugins/cache/presales-skills/ai-image/*/skills/gen/requirements.txt
```

> 维护者注意：不要手写 `python -c "import X"` 验证依赖（曾踩过 cssutils 这种导入名 ≠ 包名的虚报缺失 case）。`requirements.txt` + `_ensure_deps.py` 才是单一权威。详见 [CLAUDE.md §4.7](../CLAUDE.md#47-自动依赖安装_ensure_depspy-是权威)。

---

## 5. 系统级依赖（非 Python）

### macOS

```bash
brew install pandoc cairo
brew install --cask drawio                   # 可选，drawio plugin 用
```

### Debian / Ubuntu

```bash
apt install pandoc libcairo2-dev
```

### Windows

见 [docs/cross-agent.md §3](cross-agent.md#3-windows-适配)。
