# 第三方组件来源声明

ppt-master plugin 在构建过程中从以下第三方开源项目 vendor（借用 + 改写）了主体代码和文档。所有借用内容均遵守原项目的 MIT 许可证，并在本文件中集中标注出处。

## hugohe3/ppt-master

- **项目主页**：https://github.com/hugohe3/ppt-master
- **作者**：Hugo He
- **许可证**：MIT License © 2025-2026 Hugo He
- **Vendor 源 commit**：`6c2aa7e533e194fef9b9dd95fa6e66f3615332ac`（snapshot 2026-04-26）

### 借用范围

ppt-master plugin 是基于 hugohe3/ppt-master 整仓 vendor 后，按 presales-skills marketplace 体例改造而成。原项目的主体内容（SKILL.md / scripts / references / workflows / docs / README / index.html / viewer.html / user-manual.md / 21 个内置 layouts / 项目骨架文件如 AGENTS.md / CLAUDE.md / CONTRIBUTING.md / CODE_OF_CONDUCT.md / SECURITY.md / .github/）均原样或小幅改写后保留。

### 本仓相对 upstream 的主要修改

| 类别 | 修改 | 原因 |
|---|---|---|
| 目录结构 | `skills/ppt-master/` → `skills/make/`（v1.0.0）| 消除 Claude Code `<plugin>:<plugin>` 双名（`/ppt-master:ppt-master` → `/ppt-master:make`）|
| 目录结构 | `requirements.txt` 移到 `skills/make/requirements.txt`（v1.0.0）| 修复 vercel-labs/skills CLI 装到 Codex / Cursor / OpenCode 时仅拷贝 `skills/<name>/` 单元的文件丢失问题 |
| SKILL.md frontmatter | `name: ppt-make` → `name: make` | 与新目录名对齐 |
| Python 脚本 | `skills/make/scripts/_ensure_deps.py`：`_PLUGIN_ROOT = _SCRIPTS_DIR.parent.parent.parent` → `_SKILL_DIR = _SCRIPTS_DIR.parent`；变量名同步 `_PLUGIN_ROOT` → `_SKILL_DIR` | requirements.txt 位置变更后路径计算同步 |
| 跨 plugin 引用 | 文档 + 脚本中的 image-gen 调用从历史 `image-gen` CLI 改为新形式 `Skill(skill="ai-image:gen")` / `/ai-image:gen` | 适配 presales-skills monorepo 中 ai-image plugin 的 v1.0.0 sub-skill split |
| SKILL.md 主体 | Step 3 加入 `~/.config/presales-skills/config.yaml` 字段 `ppt_master.default_layout` 全局覆盖（未设置时走 free design 默认）；opt-in 触发条件：用户明说模板名 / 风格 / 问列表 | 让用户能持久化选择默认模板，无需每次切换 |
| 模板新增 | `skills/make/templates/layouts/alauda/`（含 SVG layout + design_spec.md + component_library.md） | 本仓自添加，**非 vendored 内容**，本仓自有版权 |
| 删除 | 移除 upstream `.env.example` / `examples/` / `requirements.txt`（顶层）等与 plugin 集成无关或位置冲突的文件 | monorepo plugin 体例不再需要顶层运行环境样例；examples/ 在 plugin 安装场景下不实用 |

注：以上不是穷尽列表，详见仓 git log（`git log -- ppt-master/`）。

### hugohe3/ppt-master 原项目 LICENSE

```
MIT License

Copyright (c) 2025-2026 Hugo He

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
