# AGENTS.md — presales-skills monorepo

本文件为 Codex 在本仓库内启动会话时**自动加载**的工程纪律与硬约束。修改本仓库代码前必读。

> **每个 plugin 自带的 AGENTS.md** 提供 plugin 内部细节（结构 / 工作流 / sub-skill 关系）：
> - [solution-master/AGENTS.md](solution-master/AGENTS.md)
> - [tender-workflow/AGENTS.md](tender-workflow/AGENTS.md)
> - [ppt-master/AGENTS.md](ppt-master/AGENTS.md)
>
> 本文件覆盖跨 plugin 的 monorepo 级规则，不与 plugin 级 AGENTS.md 重复。

---

## 1. 版本号 bump 三处规则（推送远端 / 发布前必查）

版本号是给用户和 marketplace 客户端看的**远端升级信号**，不是本地 commit 计数器。本地开发 commit 可以不 bump；准备推送远端、发版、或让用户通过 `/plugin update` 获取变化时，才根据下面规则判断是否 bump。需要 bump 时，**三处版本号都要 +1**：

| # | 位置 | 字段 | 含义 |
|---|---|---|---|
| 1 | `<plugin>/.claude-plugin/plugin.json` | `version` | plugin 自己的版本——告诉客户端"有新版" |
| 2 | `.claude-plugin/marketplace.json` 中 `plugins[]` 那一条 | `version` | marketplace 目录里该 plugin 条目的版本 |
| 3 | `.claude-plugin/marketplace.json` | `metadata.version` | marketplace 自己的修订号——告诉客户端"目录变了来重抓" |

三步缺一步，客户端就拿不到更新。打比方：plugin = 书的新版；marketplace entry = 书店的书单条目；marketplace 顶层 = 书单的修订号。

### 只 bump 你改了的 plugin

**不要** "顺手" 把别的 plugin 也 +1。只 bump 改动涉及的 plugin entry，其他不动——这样用户升级只会拉到你改的，不会被误更新别的。

### 本地 commit 与远端发布分离

- **本地 commit 不要求 bump**：为了保存中间工作、review、实验、测试或拆分提交，不要因为 commit 本身修改版本号。
- **推送远端 / 发版前才 bump**：当你准备把改动推到用户会拉取的远端分支，且改动会让用户 `/plugin update` 后看到不同运行时行为或元数据时，才做三处 bump。
- **文档 / 测试 / harness 规范提交不 bump**：即使这些提交很重要，只要不改变用户运行 skill 的结果，就不制造空升级。
- **一个用户可见发布只 bump 一次**：多次本地 commit 组成同一批远端发布时，在发布前统一 bump，而不是每个 commit 都 bump。

### 关键判别准则（先看这条）

**这次改动会让用户 `/plugin update` 后看到不同的"东西"吗？**

- **运行时行为变化**（功能 / 命令 / 工作流 / 配置生效路径）→ 必须 bump
- **plugin 元数据变化**（`description` / `homepage` / `repository` / `name` / `version` 等用户可见的 marketplace 字段）→ 必须 bump
- **纯文字 nit**（typo / 删冗余 / 措辞调整 / 标点 / 排版）→ **不 bump**，无论文件位于何处

### 不需要 bump 的改动

- **仓库根级文档**：`README.md` / `AGENTS.md` / `docs/` / `tests/` / `.gitignore`（不进任何 plugin 分发物）
- **开发者 / agent 工程规范**：根目录或 plugin 内的 `AGENTS.md` / `CLAUDE.md` / 贡献指南 / harness 规范 / 测试，只影响维护者或 AI 编程纪律，不改变用户运行 skill 的结果 → **不 bump**
- **plugin 内的纯文字 nit**：plugin README/SKILL.md/workflow 内的 typo、冗余删除、措辞调整——只要不改语义、不改命令、不改流程
- **dev 工具**：`.claude/commands/`、`tests/` 内新增 / 修改

### bump level 规则（影响功能或元数据时才适用）

| 改动类型 | level | 例子 |
|---|---|---|
| 修 plugin 内 bug / 改影响用户运行时行为的文档（SKILL description / 工作流步骤 / CLI 参数 / 生成流程会读取的 reference/template 约束）/ 改 plugin 元数据（description / homepage / repository）/ 内部重构 | **patch +1** | `1.0.0 → 1.0.1` |
| 破坏性变更（删 SKILL / 改命令字符串 / 改 sub-skill dir 名 / 改公开入口 / 改 bin 命名 / 改默认行为）| **minor +1** | `1.0.0 → 1.1.0` |
| marketplace 整体重构（影响所有用户）| **major +1** | `1.x → 2.0.0`（commit message + marketplace.json description 醒目说明） |

> ⚠️ 不按"才发了几分钟"打折——破坏公开入口 = minor，不论上一版多新。
>
> ⚠️ **marketplace 顶层 bump level 至少跟随子 plugin 最高级别**：任一 plugin minor bump 时，顶层 `metadata.version` 也至少 minor。不无脑 patch +1。

### 推送远端 / 发布前复核命令

```bash
grep '"version"' .claude-plugin/marketplace.json */.claude-plugin/plugin.json
```

确认需要发布的 plugin 三处版本一致；如果本次只是本地 commit 或开发者规范 / 测试改动，确认版本号没有被误 bump。

### 双 marketplace 远端发布规则

本仓库同时发布到两个不同 marketplace，对应两个 Git remote：

| Remote | URL | 面向 |
|---|---|---|
| `origin` | `https://github.com/TubeLiu/presales-skills` | 公网用户（TubeLiu 个人 marketplace） |
| `alauda` | `https://github.com/Alauda-io/skills` | Alauda 内部用户 |

两边面向不同用户群，`README.md`、`.claude-plugin/marketplace.json`、`*/.claude-plugin/plugin.json` 中的安装命令、`homepage`、`repository` 等 repo-specific 内容必须分别指向各自仓库：

- TubeLiu 侧示例：`/plugin marketplace add TubeLiu/presales-skills`
- Alauda 侧示例：`/plugin marketplace add Alauda-io/skills`

推送远端时不要把一边的 marketplace / README / plugin metadata 直接覆盖到另一边。正确流程是：

1. 在当前侧完成代码、版本号和文档检查。
2. 推送当前侧远端（`git push origin <branch>` 或 `git push alauda <branch>`）。
3. 切换 / 准备另一侧 repo-specific 文件，只改应该不同的 marketplace / README / plugin metadata。
4. 再推送另一侧远端。
5. 分别核验两边远端的 `README.md` 安装命令、marketplace `homepage`、plugin `homepage/repository`。

注意：如果这些被 Git 跟踪的 repo-specific 文件内容不同，两边最终 tip commit hash 必然不同。不要为了追求 commit ID 相同而牺牲 marketplace 内容正确性；需要追踪同一轮源码变更时，在 commit message 或发布记录中标注共同的 source commit / source change。

---

## 2. SKILL.md / 文档自动化检查（提交前必跑）

```bash
python3 -m pytest tests/test_skill_format.py -v
```

24 项断言。任何 SKILL.md 改动 / README 改动 / 跨 plugin 引用调整，**提交前必跑**。失败修到全绿再提交。

不允许 `--no-verify` / `--skip-tests` 跳过。详见 [docs/contributing.md](docs/contributing.md)。

---

## 3. 跨 plugin 路径解析约定

跨 plugin 调用脚本时，**绝不假设兄弟相对路径**——Codex 的 cache 布局是 `<plugin>/<version>/skills/<sub-skill>/`，跨 plugin 不是兄弟。

每个 SKILL.md 顶部都有 §路径自定位 段，五段式 fallback：

1. `~/.Codex/plugins/installed_plugins.json`(Codex 权威，精确指向当前激活版本)
2. `~/.cursor/skills` / `~/.agents/skills` / `.cursor/skills` / `.agents/skills`(vercel CLI 标准目录)
3. 用户预设环境变量 `<PLUGIN>_PLUGIN_PATH`(如 `DRAWIO_PLUGIN_PATH`)
4. cwd 相对 `./` 和 `../`(dev 态)
5. 全失败 → 输出诊断 + `exit 1`(让 Codex 转述给用户，要求 export 环境变量或安装缺失 plugin)

**新增跨 plugin 调用时**：复制现有 SKILL.md 的 §路径自定位 段作为模板，不要手写。

### 跨 sub-skill（同 plugin 内）允许兄弟路径

同 plugin 内的 sub-skill 之间用 `$SKILL_DIR/../<sibling>/...` 是 OK 的。`tests/test_skill_format.py` 第 10 项断言会强制此规则——不要破坏。

---

## 4. 运行时陷阱清单

### 4.1 `${VAR}` 必须带花括号

Codex plugin 运行时**只对 `${VAR}` 做文本替换**，`$VAR`(无花括号)会**静默不替换**。错误示例：

```bash
# ❌ 错：plugin 加载时不会替换，bash 阶段 VAR 已是 literal "$VAR"
python3 $SKILL_DIR/scripts/foo.py

# ✅ 对
python3 ${SKILL_DIR}/scripts/foo.py
```

修 SKILL.md / hooks / bin 脚本时全文搜 `\$[A-Z_]+[^{}]` 检查。

### 4.2 不用 `commands/` 或 `agents/` 目录

仅用 `<plugin>/skills/<sub>/SKILL.md` 注册功能。`commands/` 仅 Codex 识别 → 加了它 = Cursor / Codex / OpenCode 用户体验降级。`agents/` 同理（且 vercel CLI 不识别）。

历史决定，不要复发。

### 4.3 `${CLAUDE_PLUGIN_ROOT}` 占位符**仅** anythingllm-mcp 的 plugin.json 用得着

普通 SKILL.md / 脚本里不要再用——已被 5 段式路径自定位取代。`tests/test_skill_format.py` 有豁免清单只放过 `anythingllm-mcp/.Codex-plugin/plugin.json`，其他文件出现就报错。

### 4.4 `command -v <bin>` 不能信

跨 plugin 找脚本不要用 `command -v`——Codex 的 plugin bin/ 是按版本路径 PATH 注入，`command -v` 在不同 cache state 下结果飘移。一律走 5 段式 fallback。

### 4.5 SKILL.md description 必须 block scalar

```yaml
# ❌ 单行 > 200 chars 会让 vercel CLI 漏识别 skill（v0.3.0 实测的 drawio bug）
description: 一长串...

# ✅
description: >
  一长串...
```

### 4.6 SKILL.md 必含 §跨平台兼容性 checklist + `<SUBAGENT-STOP>` 段

新增 SKILL.md 时**复制现有 SKILL.md 头部模板**，不要手写。

### 4.7 自动依赖安装：`_ensure_deps.py` 是权威

不要手写 `python -c "import X"` 验证依赖（曾经踩过：cssutils 这种导入名 ≠ 包名的 case 会虚报缺失）。`requirements.txt` + `_ensure_deps.py` 才是单一权威。

---

## 5. 不要写的东西

- **bundled 大体积资产**：`/plugin-review` 维度 H 专门盯这个。新增模板 / 字体 / 图片资产前先评估是否可以 lazy fetch
- **`commands/` 或 `agents/` 目录**：见 §4.2
- **跨 plugin 兄弟相对路径**：见 §3
- **手写 import 验证依赖**：见 §4.7
- **plugin 间循环依赖**：共享 plugin（ai-image / web-access / drawio / anythingllm-mcp）不能反向调用主 plugin（solution-master / ppt-master / tender-workflow）

---

## 6. Harness Engineering 规范（防穷举 / 防硬编码）

改进生成质量时，必须把问题抽象成可复用的 harness / contract / semantic layer，禁止只为某个样张、某个客户名、某句标题、某种颜色或某组坐标写一次性补丁。

### Anti-Hardcoding Harness Rule

- **禁止穷举式修样张**：不得以页面标题、客户名、固定中文文案、固定页码作为布局判断条件。
- **禁止把颜色 / 宽高 / 坐标当主语义**：颜色、尺寸、位置只能作为 fallback 证据；主判断必须来自 `component -> slot -> text`、`visual_archetype`、`density_contract`、`semantic_routes` 或显式 `data-role` / `data-slot`。
- **新增规则必须能泛化**：每个质量修复至少配 2-3 个不同页型 fixture 或 eval case，证明不是只修一张截图。
- **先修上游契约，再修 SVG**：重复质量问题优先修 planner、`design_spec.md`、`spec_lock.md`、component semantics、checker 或 retry harness；不得长期靠手工 patch SVG。
- **信息密度是契约，不是审美口号**：PPT 生成必须区分留白与稀疏。复杂页应通过 `density_contract` 明确 visible objects / labels / evidence / relationships 的最低展示量，避免把内容过度藏进 speaker notes。
- **例外要显式建模**：如果确实需要左对齐、低密度、非对称布局或弱化某些信息，必须在语义层说明原因，而不是靠局部 if-else 绕过 checker。

### 提交前验证

涉及 `ppt-master` 生成质量、SVG 布局、checker、planner、eval harness 的改动，除常规测试外还必须跑相关专项测试，并确认报告能解释“为什么更接近人类制作”，而不只是某一张样张分数上升。

---

## 7. 进一步阅读

- 用户向：[README.md](README.md) / [docs/quickstart 留在 README]
- 架构原理：[docs/architecture.md](docs/architecture.md)
- 跨 agent 兼容：[docs/cross-agent.md](docs/cross-agent.md)
- 配置详解：[docs/configuration.md](docs/configuration.md)
- 贡献者指南：[docs/contributing.md](docs/contributing.md)
