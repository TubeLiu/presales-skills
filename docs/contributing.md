# 贡献者指南

本文件覆盖：开发者工具、自动化检查、提 PR 的流程。

> 修改代码前**必读**仓库根 [CLAUDE.md](../CLAUDE.md)——版本号 bump、跨 plugin 路径、运行时陷阱等硬约束。Claude Code 会自动加载 CLAUDE.md，但人类维护者也要主动看一遍。

---

## 1. 开发者工具

### `/plugin-review`：发版前深度体检

仓库内置一条针对本 monorepo 量身定制的深度 review slash command（`.claude/commands/plugin-review.md`），用于在发版或重构前对**待发布的某个 plugin 或全部 plugin** 做穷尽式体检，产出 `REVIEW_FINDINGS.md` 供后续 plan 模式直接消费。**只读不写**：不改代码、不改 marketplace.json、不 commit、不 `/reload-plugins`。

#### 用法（在 Claude Code 会话里）

```
/plugin-review                       # 全量审查
/plugin-review solution-master       # 聚焦某个 plugin
```

聚焦单 plugin 时，元数据一致性与跨 plugin 依赖两个维度仍会跨 plugin 扫，因为这两维度本身就跨插件。

#### 触发后会发生什么

1. **阶段 1 速写**（Bash / Read 串行）→ 15 行项目快照：从 `marketplace.json` 实际枚举的所有 plugin `name@version`、SKILL 总数、bin / hook / MCP 清单、最近 commit、可疑未跟踪物
2. **阶段 2 并行 8 个 Explore agent**（单条消息并发 spawn）→ 每个维度独立深挖，主上下文只收摘要：
   - **A.** 元数据一致性审计（marketplace.json ↔ plugin.json ↔ README 三处版本号）
   - **B.** SKILL frontmatter 与触发质量（description 能否被 Claude 正确识别）
   - **C.** Plugin runtime 陷阱（`$VAR` 不带花括号的静默失效 bug、bin 命名冲突、shebang）
   - **D.** 跨 plugin 依赖健康度（可选依赖的降级分支是否真的实现）
   - **E.** Bin 脚本质量（subprocess 安全、跨平台路径、密钥泄露、`_ensure_deps.py` 健壮性）
   - **F.** Hook 安全与稳定性（SessionStart 注入失败阻塞会话风险）
   - **G.** MCP server 与配置管理（`~/.config/` 多路径迁移覆盖度、密钥权限）
   - **H.** 发布物卫生（避免 bundled 大体积资产复发）
3. **阶段 3 交叉验证** → 把 `[推断]` 用 Read / Grep 核实或降级删除，跨 agent 去重
4. **阶段 4 落盘** → 生成 `REVIEW_FINDINGS.md`（已在 `.gitignore` 中，不入库），含缺陷清单、按 plugin / 维度分组索引、修复批次建议（Batch A/B/C/D）
5. **阶段 5 交接** → 6 行总结 + 建议进 plan 模式处理 Batch A

#### 维护提醒

下次插件拓扑变化（新增 plugin、调整依赖、引入新 hook 或 MCP）时，记得回头更新 `.claude/commands/plugin-review.md` 里的"项目知识底座"章节——它是给 agent 的事实基线，过时会误导审查。

---

### `tests/test_skill_format.py`：SKILL.md / 文档自动化检查

```bash
python3 -m pytest tests/test_skill_format.py -v
```

24 项断言（含基础格式 + skill-specific 业务规则 + MCP wizard lint），**每次提 PR 前必跑**。覆盖：

- SKILL.md 必须用 block scalar `description: >`（避免 vercel CLI 解析失败）
- 含 §跨平台兼容性 checklist + `<SUBAGENT-STOP>` 段
- 不引用已删的 `commands/` 路径 / `${CLAUDE_PLUGIN_ROOT}` 占位符（仅 anythingllm-mcp 豁免）
- 不用 `command -v <bin>`（统一走 5 段式 installed_plugins.json fallback）
- vercel CLI 实测识别 13 skills（draw / image-gen / browse / solution-master / make / taa / taw / tpl / trv / twc / optimize / research / polish）
- 跨 sub-skill `$SKILL_DIR/../<sibling>/` 引用必须是同 plugin 真实 sibling
- subagent prompt body 含工具限制段
- taw writer 标题去编号 / reviewer STATUS 协议 / image_plan 字段结构 / SKILL.md ≤ 500 行
- tender-workflow 无残留 `docs/` 链接
- mcp_installer.py 含三 provider TEMPLATES + sk-cp- 校验 + understand_image
- twc / sm setup.md 含 minimax + sk-cp- + WA_INSTALLER 探针
- web-access README 暴露 mcp_installer / tender-workflow README MCP 段含 minimax

CI / 提 PR 前必跑，失败修到全绿再提交。**不允许** `--no-verify` 跳过。

---

### `tests/test_ensure_deps_identity.py`：依赖装载身份检查

确保 `_ensure_deps.py` 跨 plugin 一致（同一份逻辑被复制到多个 plugin 的 skills/ 下，避免实现漂移）。

---

## 2. 提 PR 流程

### 提交前 checklist

```bash
# 1. lint 全绿（4 文件 76+ 项）
python3 -m pytest tests/ -v

# 2. 三处版本号已 bump（仅当改动影响 plugin 分发物时；详见 CLAUDE.md §1）
grep '"version"' .claude-plugin/marketplace.json */.claude-plugin/plugin.json

# 3. 涉及多 plugin / 大改动时跑深度体检
/plugin-review

# 4. /reload-plugins 实测安装路径正确
```

> 仅改仓库根级文档（`README.md` / `CLAUDE.md` / `docs/`）或 `tests/` 时，跳过 #2-#4，只跑 #1。

### 版本号 bump 规则

完整规则见 [CLAUDE.md §1](../CLAUDE.md#1-版本号-bump-三处规则每次提交必查)。要点：

- **判别准则**：这次改动会让用户 `/plugin update` 后看到不同运行时行为吗？是 → bump；否 → 不动版本号
- **不需要 bump 的改动**：仓库根 `README.md` / `CLAUDE.md` / `docs/` / `tests/` / `.gitignore`（不进任何 plugin 分发物）
- **三处都改**（影响分发时）：plugin 自己的 `plugin.json` + marketplace.json 中该 plugin entry + marketplace.json 顶层 metadata
- **只改你动了的 plugin**：不要顺手把别的 plugin entry 一起 +1
- **bump level**：plugin 内 bug fix / plugin 内文档 = patch；公开入口破坏 = minor；marketplace 整体重构 = major
- **顶层至少跟随子 plugin 最高级别**：任一 plugin minor bump 时顶层也至少 minor

### commit message 风格

参考最近的 commit log：

```bash
git log --oneline -20
```

习惯：`<type>(<scope>): <一句话>` + 必要时正文展开"为什么"。type 用 `feat` / `fix` / `refactor` / `chore` / `docs` / `test`。scope 用 plugin 名（`ai-image` / `tender-workflow` / `taw` 等）。

---

## 3. 新增 plugin 的 checklist

如果新加一个 plugin（第 11 个或后续），需要：

1. `<plugin>/.claude-plugin/plugin.json`（含 `version`）
2. `<plugin>/skills/<name>/SKILL.md`（参照现有 SKILL.md 头部模板：frontmatter + §路径自定位 + §跨平台兼容性 checklist + `<SUBAGENT-STOP>`）
3. `.claude-plugin/marketplace.json` 加一条 entry（顶层 `metadata.version` 也要 bump）
4. `<plugin>/CLAUDE.md`（plugin 内部细节，参照 `solution-master/CLAUDE.md` / `tender-workflow/CLAUDE.md`）
5. 在 [README.md](../README.md) / [README_EN.md](../README_EN.md) 的 10 plugin 分组表里加一行，并确认它属于 Base Tools / Presales Workflows / Writing & Meta 哪一组
6. 跑 `python3 -m pytest tests/ -v`，通常 `test_skill_format.py` 会发现新 plugin 自动断言（如果用了豁免清单则手动加）
7. 视情况更新 `.claude/commands/plugin-review.md` 的"项目知识底座"

---

## 4. 进一步阅读

- 工程纪律权威源：[CLAUDE.md](../CLAUDE.md)
- 设计原理：[docs/architecture.md](architecture.md)
- 跨 agent 兼容：[docs/cross-agent.md](cross-agent.md)
- 配置详解：[docs/configuration.md](configuration.md)
