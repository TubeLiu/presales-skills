---
description: 对 presales-skills monorepo 做穷尽式深度 review，产出 REVIEW_FINDINGS.md 供 plan 模式消费
argument-hint: "[可选：聚焦的 plugin 名，如 solution-master；留空则全量审查]"
---

# presales-skills 深度 Review（为 plan 模式铺路）

## 目标
对本 monorepo 的 **待发布 plugin 或全部 plugin** 进行穷尽式 review，产出 `REVIEW_FINDINGS.md`，供 plan 模式直接消费。**只读不写**：不改代码、不改 marketplace.json、不 commit、不 `/reload-plugins`。

**plugin 清单不得写死**：由 `.claude-plugin/marketplace.json` 的 `plugins[].name` 与根目录下对应的 `<name>/.claude-plugin/plugin.json` 实际枚举得到。若 `$ARGUMENTS` 非空，将审查范围收窄到该 plugin，但**元数据一致性（阶段 2-A）和跨 plugin 依赖（阶段 2-D）仍需覆盖全量**，因为这两个维度本身就是跨 plugin 的。

## 项目知识底座（review 时必须默认的事实）

> 以下具体 plugin 名 / bin 名 / 路径是**编写时的快照**，仅作为理解项目形态的参考。实际 review 中一切清单（plugin、bin、hook、MCP、依赖关系）必须由阶段 1 从 `marketplace.json` 和文件系统**重新枚举**，不要把快照当闭集。

- 根 `.claude-plugin/marketplace.json` 是唯一入口，字段 `plugins[].version` 必须与 `<plugin>/.claude-plugin/plugin.json` 的 `version` 一致
- **三处版本号**：`plugin.json` + `marketplace.json` 条目 + README 徽章/说明。发版时三处必须同步（README commit `5560b93` 明确留了这条 reminder）
- **Plugin runtime 陷阱**：
  - 只有 `${VAR}` 带花括号才会被文本替换；`$VAR` 不带花括号**静默失效**。凡是 `plugin.json` / `SKILL.md` / hooks 配置里出现 `$` 的地方必须审查
  - plugin `bin/` 目录会自动加入 PATH
  - 本地 marketplace 原地加载（no copy）
- **依赖拓扑**（快照，实际以 marketplace.json 的 description 字段和代码中的实际调用为准）：
  - solution-master → drawio（必需）、ai-image（必需）、anythingllm-mcp（可选降级）、web-access（仅 cdp_sites.enabled=true 时必需）
  - tender-workflow → drawio、ai-image、anythingllm-mcp（可选）
  - ppt-master → ai-image
- **bin 入口**（快照，实际以各 plugin `bin/` 目录枚举为准）：`drawio-gen`、`image-gen`、`ai-image-config`、`web-access-check`、`web-access-match-site`、`solution-master.js`。命名冲突会破坏 PATH 行为
- **hook**（快照）：solution-master 的 `hooks/hooks.json` 做 SessionStart 铁律注入 —— 任何会话都会跑
- **MCP**（快照）：anythingllm-mcp 通过 stdio，0 npm 依赖
- **自动装依赖**：ppt-master / ai-image 入口脚本调用 `_ensure_deps.py` + `.deps-installed` marker，版本号变更会失效 marker

## 工作流

### 阶段 1：清点（直接用 Bash/Read，不派 agent）
并行执行以下快速侦察：
- `git log --oneline -50` 看近期动向（是否有 revert、是否有"fix" commit 堆积）
- `git status` + `git ls-files --others --ignored --exclude-standard` 查未跟踪 / 被忽略的可疑物
- Glob `**/.claude-plugin/plugin.json` 全量读取，提取 `name/version/description` 三元组
- Glob `**/SKILL.md` 全量读取 frontmatter（name/description/allowed-tools）
- 读 `.claude-plugin/marketplace.json` 与各 `plugin.json` 对齐 version
- `du -sh */` 查每个 plugin 大小（ppt-master 之前有 92MB bundled examples 的历史，警惕复发）
- `find . -name "*.py" -o -name "*.js" -o -name "*.sh"` + `-path "*/bin/*"` 列出所有 bin 脚本

输出 ≤15 行"项目速写"，内容：**当前 marketplace 中所有 plugin** 的 `name@version`（以枚举结果为准，不要假设数量）、skill 总数、bin 脚本清单、hook 清单、MCP server 清单、最近 5 次 commit 主题、可疑的未跟踪文件。

### 阶段 2：并行深挖（单条消息 spawn 多个 Explore agent）

**必须在同一条消息里并发发出下列 agent 调用**。每个 agent 的 prompt 要自包含（它看不到本提示词），明确要求所有发现带 `file:line`、区分 `[事实]/[推断]`、只读不写。

| # | Agent | 范围 | 必查项 |
|---|-------|------|--------|
| A | **元数据一致性审计** | `.claude-plugin/marketplace.json` + 所有 `plugin.json` + README | 三处版本号同步？marketplace 声明的依赖与实际代码调用匹配？description 字段是否过时（如 ppt-master README 最近刚 fix `image_gen.py` → `image-gen`，查是否还有残留）？`author/category/tags` 字段完整？|
| B | **Skill frontmatter 与触发质量** | 全部 `SKILL.md` | `name/description` 合规？description 是否包含清晰的触发信号（"当…时使用"、场景关键词）？是否与其他 skill 语义冲突？`allowed-tools` 是否合理（过宽给太大权限，过窄可能导致 skill 失效）？是否引用了不存在的子文件？|
| C | **Plugin runtime 陷阱** | 所有 `plugin.json` / `SKILL.md` / `hooks.json` / `hooks-cursor.json` / bin 脚本内部字符串 | 出现 `$VAR` 不带花括号且意图是变量替换的地方（**静默 bug**）？`${CLAUDE_PLUGIN_ROOT}` 等运行时变量用法正确？hard-coded 绝对路径？bin 名称冲突？shebang 正确（`#!/usr/bin/env ...`）且可执行？|
| D | **跨 plugin 依赖健康度** | 主 plugin 对共享 plugin 的所有调用点 | solution-master / tender-workflow / ppt-master 对 `drawio-gen` / `image-gen` / `web-access-*` 的调用是走 PATH 还是相对路径？可选依赖（anythingllm-mcp / web-access）的降级分支是否真的实现了还是会直接崩？marketplace 声明的依赖与实际 import/spawn 调用是否对齐？|
| E | **Bin 脚本质量** | `*/bin/*` 与被调用的 Python/Node 模块 | 错误处理（subprocess 失败、文件不存在、key 未配置）？跨平台路径（`os.path` vs 硬编码 `/`）？危险 subprocess（shell=True + 用户输入拼接）？密钥是否可能泄露到日志/错误信息？`_ensure_deps.py` + `.deps-installed` marker 的版本失效逻辑是否健壮？|
| F | **Hook 安全与稳定性** | `solution-master/hooks/hooks.json` + `hooks-cursor.json` | SessionStart 注入失败会不会阻塞会话？注入文本是否过长（吃上下文）？hook command 是否跨平台？是否有 side effect（写文件、网络请求）？|
| G | **MCP server 与配置管理** | `anythingllm-mcp/` 全部 + 所有 `~/.config/*` 相关代码 | MCP stdio 异常退出的恢复？protocol 版本协商？配置路径 `~/.config/presales-skills/` vs `~/.config/solution-master/` vs `~/.config/tender-workflow/` 的迁移路径是否覆盖所有历史版本？密钥存储权限（0600）？|
| H | **发布物卫生** | git tracked files + .gitignore + 每个 plugin 根目录 | 是否有 >1MB 的二进制或示例物残留（ppt-master 92MB 惨案再现风险）？`.pytest_cache` / `output/` / `drafts/` 是否应该被 ignore？`.DS_Store`？Python `__pycache__`？秘钥文件？|

### 阶段 3：交叉验证
子智能体返回后：
1. 对每条 `[推断]` 用 Read/Grep 亲自核实，能升 `[事实]` 就升，站不住脚就删
2. 跨 agent 去重（例如"version 不一致"可能同时出现在 A、D 中 → 合并）
3. **关键对账**：拿阶段 1 速写里枚举出的全部 `name@version`，和阶段 2-A 的发现做最后一次对齐，确保没有 agent 看漏任何 plugin

### 阶段 4：分级与产出

严重度判据（针对本项目，不要套通用标准）：
- **P0 阻塞**：
  - 任何会让 `/plugin install` 或 `/reload-plugins` 失败的问题
  - hook 导致 SessionStart 崩溃
  - 密钥泄露
  - marketplace.json 字段错误导致插件无法被发现
- **P1 严重**：
  - 版本号三处不一致（已发布状态下）
  - `$VAR` 不带花括号的静默失效 bug
  - bin 名称冲突
  - skill description 写得让 Claude 识别不到（skill 变成"摆设"）
  - 可选依赖声明"可降级"但代码里没降级分支
- **P2 一般**：可维护性、错误信息不友好、文档漂移
- **P3 优化**：锦上添花

**写入 `REVIEW_FINDINGS.md`**（项目根），结构：

```markdown
# presales-skills 深度 Review 发现清单

生成时间：<date>
审查 commit：<sha>
审查范围：<N> plugins / <M> skills / <K> bin entries / <H> hooks / <S> MCP servers（按阶段 1 实际枚举填写）

## 项目速写
<阶段 1 的 15 行摘要>

## 缺陷清单

### F-001 [P1][元数据] solution-master 三处版本号漂移
- **位置**：
  - `solution-master/.claude-plugin/plugin.json:4` → `"version": "0.1.6"`
  - `.claude-plugin/marketplace.json:XX` → `"version": "0.1.6"`
  - `README.md:LINE` → 表格未更新仍显示 0.1.5
- **[事实]** README 表格的版本栏与 plugin.json 不一致
- **影响**：用户安装后看到的版本与文档不符；不阻塞但会在下次发版被 linter 捕获
- **修复方向**：对齐 README；或抽出版本号生成脚本
- **工作量**：<1h
- **所属 plugin**：solution-master

### F-002 ...

## 按 plugin 分组索引
- **drawio**：F-00X, F-00Y
- **ai-image**：...
- **solution-master**：...
（让 plan 模式能按 plugin 批量修）

## 按维度分组索引
- **元数据一致性**：F-00X, ...
- **runtime 陷阱**：...
- **依赖降级**：...

## 统计
- P0: N / P1: N / P2: N / P3: N
- 预计总工作量：N 人日

## 修复批次建议（供 plan 模式参考）
1. **Batch A（发版阻塞，优先修）**：列出所有 P0 + 版本号类 P1
2. **Batch B（runtime 正确性）**：`$VAR`/bin 冲突/依赖降级
3. **Batch C（skill 触发质量）**：description 重写、allowed-tools 收敛
4. **Batch D（卫生与文档）**：.gitignore、README 漂移、文件清理
```

### 阶段 5：交接
输出 ≤6 行总结：
- 发现总数与分布
- 最紧急的 3 条（每条一句话 + file:line）
- 明确提示："建议进入 plan 模式，先处理 Batch A"
- 提醒是否需要把 `REVIEW_FINDINGS.md` 加到 `.gitignore`（它是临时产物）

## 铁律
1. **只读不写**：本阶段禁止修改任何文件、禁止 `/reload-plugins`、禁止 commit
2. **引用必须实存**：每个 `file:line` 要真实；禁止凭印象
3. **事实/推断分离**：未验证不写成事实
4. **并行优先**：阶段 2 的 8 个 agent 必须在**同一条消息**内 spawn
5. **聚焦本项目**：不写"建议加 CI/CD"、"建议写单测"这类脱离 plugin 项目实际的通用建议 —— plugin 项目的主要质量门槛是**元数据 / runtime / skill 触发**，不是算法
6. **不越界**：不写修复代码、不写 plan，那是下一阶段

## 开始
不要再向用户确认，直接进入阶段 1。
