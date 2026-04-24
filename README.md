# presales-skills — 售前工作流 Claude Code plugin 集

售前场景下的 AI 辅助工作流打包，通过 Claude Code plugin marketplace 统一分发。目前包含三个主 plugin：

- **solution-master**：通用解决方案撰写框架（苏格拉底式需求提取、子智能体驱动撰写、双重审查、多源知识检索、上下文感知配图）
- **ppt-master**：从 PDF/DOCX/URL/MD 等多源文档生成专业 PPT（中间经过 SVG 流水线，最终导出为 PPTX）
- **tender-workflow**：四角色招投标工作流——`tpl`（招标策划）/`taa`（招标分析）/`taw`（标书撰稿）/`trv`（审核）+ `twc`（配置）

> **计划中的共享 plugin**（后续 Milestone 接入）：`drawio`（从 solution-master 独立出来）、`ai-image`（统一 AI 图片生成，三方共用）。当前版本下，三方各自保留内置实现。

## 安装

### 方式 A：GitHub 远程订阅（推荐，发布后可用）
```
/plugin marketplace add Alauda-io/presales-skills
/plugin install solution-master@presales-skills
/plugin install ppt-master@presales-skills
/plugin install tender-workflow@presales-skills
```

### 方式 B：本地开发模式
```
git clone https://github.com/Alauda-io/presales-skills.git
/plugin marketplace add /path/to/presales-skills
/plugin install solution-master@presales-skills
...
```

更新订阅（远程订阅默认不自动更新）：
```
/plugin marketplace update presales-skills
```

## 依赖

- **ppt-master**：需 `pip install -r ~/.claude/plugins/*/ppt-master/requirements.txt`（python-pptx、cairosvg、PyMuPDF 以及 AI 图生 SDK 等）
- **tender-workflow**：首次运行 `/twc` 自动安装 pyyaml；AnythingLLM MCP server 已内置（纯 Node 内置模块，零依赖）
- **solution-master**：AnythingLLM MCP server 已内置；所需 Python 依赖由 skill 内脚本按需安装

## 开发说明

本仓库由原 `TubeLiu/{solution-master, ppt-master, tender-workflow}` 三个独立 GitHub 仓库在 Alauda-io 组织下合并而来。合并后历史起点以本仓库为准。

三个子目录保留完整项目结构，既可作为 Claude Code plugin 统一安装，也可各自独立 clone + cd 进去用源码模式工作。

后续 Milestone 路线见 plan（5 里程碑：骨架 → 探针 → 跨 plugin 重构 → ai-image 统一 → 验证发布）。

## 许可

各子项目沿用自身许可（均为 MIT，详见 `<子项目>/LICENSE`）。
