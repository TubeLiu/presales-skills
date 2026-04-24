### E1 — Plugin 模式下 SessionStart hook 激活

**目的**：验证以 Claude Code Plugin 方式安装 Solution Master 后，会话启动时铁律被注入。

**正确的本地 plugin 安装流程**（Claude Code 要求先把本地目录加为 marketplace，再从该 marketplace 安装具体 plugin）：

```
/plugin marketplace add /Users/tubeliu/Library/CloudStorage/OneDrive-个人/personal-project/solution-master
/plugin install solution-master@solution-master
/reload-plugins
```

说明：
- 第一个命令把 `solution-master/.claude-plugin/marketplace.json` 所在目录注册为本地 marketplace
- 第二个命令从中安装名为 `solution-master` 的 plugin（完整格式是 `<plugin-name>@<marketplace-name>`，两者都叫 `solution-master`）
- 第三个命令 reload 使 SessionStart hook 立即生效（也可以退出会话后重新启动 `claude`）

**步骤**：

1. 在一个空目录创建 SM 项目标志：
   ```bash
   mkdir -p /tmp/sm-e1/drafts && cd /tmp/sm-e1
   ```
2. 启动 Claude Code：
   ```bash
   claude
   ```
3. 在会话中按上面顺序执行三条斜杠命令
4. 用 `/plugin list` 或 `/plugin` 确认 `solution-master` 在 Installed 列表
5. 退出重启会话（或 `/reload-plugins` 已跑过就直接继续）
6. 向 Claude 发问：「复述 Solution Master 的 7 条铁律」

**预期**：Claude 能无需查找文件直接复述，说明 `using-solution-master` SKILL 已通过 SessionStart hook 注入 `additionalContext`。

**卸载命令**：
```
/plugin uninstall solution-master@solution-master --scope local
/plugin marketplace remove solution-master
```

**回填**：`____ PASS / FAIL`，备注：______________

---

### E2 — 子智能体"不信任报告"原则（Layer 2 验证）

**目的**：验证 spec-reviewer / quality-reviewer 被分派时会真的读 draft 文件，而不是只看撰写者汇报。

**步骤**：

1. 接续 E1 会话
2. 人为制造一个缺陷场景：让 Claude 先写一个 mock 章节 `drafts/e2_test.md`，正文故意遗漏计划要求的某个要点（例如计划要求"包含 3 个案例"但只写了 2 个）
3. 然后让 Claude 对该章节执行 spec-reviewing

**预期**：
- spec-reviewer 子智能体会用 Read 工具打开 `drafts/e2_test.md`
- 它会在审查报告中把"只有 2 个案例"作为 FAIL 项列出来
- 它**不会**仅仅信任撰写者的"我写了 3 个案例"声明

**回填**：`____ PASS / FAIL`，备注：______________

---

### E3 — 非 SM 项目隔离

**目的**：验证 SessionStart hook 的项目门禁。

**步骤**：

1. `cd /tmp && mkdir -p random-proj && cd random-proj`（**不**创建 `drafts/` 或 `docs/specs/`）
2. 启动 `claude`
3. 观察是否有 SM 铁律注入

**预期**：
- SessionStart hook 静默（不注入）
- 向 Claude 提问「复述 Solution Master 的铁律」，Claude 应该回答"不知道"或去项目里找文件——说明没有被注入

**回填**：`____ PASS / FAIL`，备注：______________

---

### E4 — npx 项目模式端到端

**目的**：验证非插件安装路径端到端工作。

**步骤**：

1. `cd /tmp && mkdir -p sm-e4 && cd sm-e4 && mkdir drafts`
2. 运行：
   ```bash
   node /Users/tubeliu/Library/CloudStorage/OneDrive-个人/personal-project/solution-master/bin/solution-master.js
   ```
3. 验证 `.claude/skills/`、`.claude/agents/`、`.claude/hooks/`、`.claude/settings.json` 就位
4. 启动 `claude`，让它复述铁律

**预期**：安装成功 + 会话启动后 Claude 能复述铁律。

**回填**：`____ PASS / FAIL`，备注：______________

---

### E5 — npx 全局模式端到端

**目的**：验证全局模式下 SM 项目生效、非 SM 项目隔离。

**步骤**：

1. 运行：
   ```bash
   node /Users/tubeliu/Library/CloudStorage/OneDrive-个人/personal-project/solution-master/bin/solution-master.js --global
   ```
2. 验证 `~/.claude/skills/using-solution-master/` 就位、`~/.claude/settings.json` 含 SessionStart hook
3. 在一个 SM 项目和一个非 SM 项目分别启动 `claude` 测试行为
4. 测完卸载：`node .../bin/solution-master.js --uninstall --global`

**预期**：SM 项目生效；非 SM 项目静默；卸载后清理干净。

**回填**：`____ PASS / FAIL`，备注：______________

---

### E6 — 连续 install / uninstall 干净

**目的**：验证多次安装卸载后状态与初始一致。

**步骤**：

1. 选一个干净的临时项目目录
2. 连续跑两轮：
   ```bash
   node .../bin/solution-master.js
   node .../bin/solution-master.js --uninstall
   node .../bin/solution-master.js
   node .../bin/solution-master.js --uninstall
   ```
3. 检查 `.claude/` 目录：应只剩安装前存在的文件（或被清空）

**预期**：没有残留的 SM 资产或 hook 条目；如果安装前没有 `.claude/settings.json`，卸载后它可能仍然存在（空壳或仅含用户其他配置），但 SM 相关部分全部移除。**特别注意**：`skills/drawio` 也应该被清理掉（动态派生的技能列表）。

**回填**：`____ PASS / FAIL`，备注：______________
