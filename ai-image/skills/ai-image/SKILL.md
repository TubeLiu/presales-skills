---
name: image-gen
description: >
  AI 图片生成统一入口。覆盖 13 个后端
  （volcengine/ark、qwen/dashscope、gemini、openai、minimax、stability、bfl、
  ideogram、zhipu、siliconflow、fal、replicate、openrouter）。
  触发场景包括：
  「生成图片 / 做配图 / AI 画图 / 生成一张插图 / 画一张 / generate image /
  AI image / make illustration」（生图）；
  「配置 ai-image / setup ai-image / 初始化 ai-image / 我刚装新版需要初始化 /
  reconfigure ai-image」（首次/重新配置）；
  「设置 ark key / 改默认图片 provider / set api key / change default model」（设置）；
  「查看图片配置 / show config / 看一下当前 ai-image 配置」（查看）；
  「列出图片模型 / list image models / 看支持哪些图片 provider」（列模型）；
  「验证 API key / validate api key / 健康检查 ai-image」（验证）；
  「加自定义图片模型 / add custom image model / 注册新 provider」（添加模型）；
  「迁移旧 ai-image 配置 / migrate config / 合并 ai-image config」（迁移）。
  统一读取 ~/.config/presales-skills/config.yaml 获取 API key。
allowed-tools: Read, Write, Bash, Glob, Grep
---

# ai-image Skill — 统一 AI 图片生成

> **跨平台兼容性 checklist**（Windows / macOS / Linux）：
> 1. **Python 命令名**：示例用 `python3`。Windows 不可识别时改 `python` 或 `py -3`。
> 2. **路径自定位**：本文档所有脚本路径用下方 §路径自定位 一节的 bootstrap 解析。
> 3. **可执行检测**：用 `which`/`where`/`Get-Command`，不用 `command -v`。
> 4. **Bash heredoc / `&&` / `||`**：Windows cmd 不支持，建议在 Git Bash / WSL2 中运行。
> 5. **路径分隔符**：用正斜杠 `/`，避免硬编码反斜杠 `\`。

<SUBAGENT-STOP>
此技能是给协调者读的。**判定你是否子智能体**：如果你的当前角色定义来自 Task prompt 而非 SKILL.md 自然加载（即调用方在 Task 工具的 prompt 字段里塞了 agents/<role>.md 的内容），你就是子智能体；跳过本 SKILL.md 的工作流编排部分，只执行 Task prompt 给你的具体任务。
</SUBAGENT-STOP>

ai-image 是 presales-skills marketplace 的共享 plugin，为 solution-master / ppt-master / tender-workflow 三个主 plugin 提供统一的图片生成能力。

## 路径自定位

**首次调用本 skill 的脚本前，先跑一次以下 bootstrap 解析 SKILL_DIR**（后续命令用 `$SKILL_DIR/scripts/...`）：

```bash
SKILL_DIR=$(python3 -c "
import json, os, sys
p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(p):
    d = json.load(open(p))
    for entries in d.get('plugins', {}).values():
        for e in (entries if isinstance(entries, list) else [entries]):
            if isinstance(e, dict) and '/ai-image/' in e.get('installPath', ''):
                print(e['installPath'] + '/skills/ai-image'); sys.exit(0)
" 2>/dev/null)

# vercel CLI fallback
[ -z "$SKILL_DIR" ] && for d in ~/.cursor/skills ~/.agents/skills .cursor/skills .agents/skills; do
    [ -d "$d/ai-image/skills/ai-image" ] && SKILL_DIR="$d/ai-image/skills/ai-image" && break
    [ -d "$d/ai-image" ] && SKILL_DIR="$d/ai-image" && break
done

# 用户预设环境变量
[ -z "$SKILL_DIR" ] && [ -n "${AI_IMAGE_PLUGIN_PATH:-}" ] && SKILL_DIR="$AI_IMAGE_PLUGIN_PATH/skills/ai-image"

# dev 态
[ -z "$SKILL_DIR" ] && [ -d "./ai-image/skills/ai-image" ] && SKILL_DIR="$(pwd)/ai-image/skills/ai-image"

if [ -z "$SKILL_DIR" ]; then
    echo "[ERROR] 找不到 ai-image skill 安装位置。" >&2
    echo "请设置：export AI_IMAGE_PLUGIN_PATH=/path/to/ai-image" >&2
    exit 1
fi
```

**错误恢复 protocol**：bootstrap 退出 1 时不要重试，把 stderr 转述给用户并请求 `/plugin install ai-image@presales-skills` 或手工 export 环境变量。

## 工作流（生成图片场景）

1. **读取用户意图**：图片主题、风格、尺寸、数量
2. **选 provider**：按场景 + 用户默认偏好（来自 `~/.config/presales-skills/config.yaml` 的 `ai_image.default_provider`）
3. **准备 prompt**：如果用户只给了简要主题，扩展为详细描述
4. **执行生成**：调 `image_gen.py`：
   - 设定 `IMAGE_BACKEND` 为选定 provider 的 canonical 名（ark→volcengine，dashscope→qwen，其他同名）
   - 通过 `-o` 指定输出目录
   - 根据 `ai_image.default_size` 或用户显式指定的 aspect ratio / size

```bash
# 默认 provider（来自 config.yaml）
python3 "$SKILL_DIR/scripts/image_gen.py" "用户提示词" --aspect_ratio 16:9 --image_size 1K -o /path/to/output/

# 显式指定 backend
IMAGE_BACKEND=ark python3 "$SKILL_DIR/scripts/image_gen.py" "用户提示词" -o /path/to/output/
```

5. **验证输出**：文件存在且 > 10KB，否则降级或报错
6. **返回给用户**：图片路径 + 简要描述

### Provider 选择策略

| 用户场景 | 推荐 provider |
|---|---|
| 中文场景、文字渲染（图表/海报）| `dashscope` (qwen-image-2.0-pro) |
| 真实感照片、高分辨率 | `ark` (Seedream 4.5 / 5.0) |
| 通用画质、英文场景 | `gemini` (2.5 Flash Image) |
| 聚合平台、多模型切换 | `openrouter` / `fal` / `replicate` |

详细列表：`python3 "$SKILL_DIR/scripts/ai_image_config.py" models`

## 配置管理（setup / show / set / models / validate / add-model / migrate 场景）

所有配置通过 `ai_image_config.py` 子命令管理。先按 §路径自定位 解析 `SKILL_DIR`，然后：

| 触发词 | 命令 |
|---|---|
| 配置 / 初始化 / 我刚装新版 | `python3 "$SKILL_DIR/scripts/ai_image_config.py" setup` |
| 查看配置 / show | `python3 "$SKILL_DIR/scripts/ai_image_config.py" show [section]` |
| 设置 / 改 key / change | `python3 "$SKILL_DIR/scripts/ai_image_config.py" set <key.path> <value>` |
| 列出模型 / list models | `python3 "$SKILL_DIR/scripts/ai_image_config.py" models [provider]` |
| 加自定义模型 / add | `python3 "$SKILL_DIR/scripts/ai_image_config.py" add-model <provider> <yaml>` |
| 验证 / validate | `python3 "$SKILL_DIR/scripts/ai_image_config.py" validate [provider]` |
| 迁移配置 / migrate | `python3 "$SKILL_DIR/scripts/ai_image_config.py" migrate` |

### 交互式配置向导（首次配置 / "帮我配置 ai-image" 触发）

**当用户说「配置 ai-image / 帮我配置 ai-image / 初始化 ai-image / setup ai-image / 我刚装好需要配置」时，按以下流程引导用户**：

```
步骤 1：解析 SKILL_DIR（用本文件 §路径自定位 段）

步骤 2：跑 setup 写默认骨架 + auto-migrate
   bash: python3 "$SKILL_DIR/scripts/ai_image_config.py" setup
   读取 stderr/stdout，告知用户结果（已迁移 / 已写骨架 / 配置已存在）

步骤 3：跑 show 展示当前配置（API keys 自动 mask）
   bash: python3 "$SKILL_DIR/scripts/ai_image_config.py" show api_keys

步骤 4：问用户想配哪些 provider（一次最少 1 个）
   询问用户："你想配置哪些 AI 图片 provider？我推荐先配以下几个常用的：
     • ark（火山方舟，Seedream 4.5/5.0，真实感照片）
     • dashscope（阿里云通义万相，中文场景 / 文字渲染）
     • gemini（Google Gemini 2.5 Flash Image，通用画质）
   你也可以选 13 个 provider 中的任意一个或多个：
     openai / minimax / stability / bfl / ideogram / zhipu / siliconflow / fal / replicate / openrouter
   请告诉我 provider 名 + 对应 API key（可分多次提供，每次一个 provider）。"

步骤 5：用户每提供一个 key，立即调 set 写入：
   bash: python3 "$SKILL_DIR/scripts/ai_image_config.py" set api_keys.<provider> <key>
   写入后立即 validate 单个 provider：
   bash: python3 "$SKILL_DIR/scripts/ai_image_config.py" validate <provider>

步骤 6：问用户默认 provider（如已配置多个）
   询问用户："默认用哪个 provider 作为生图后端？（默认 ark）"
   bash: python3 "$SKILL_DIR/scripts/ai_image_config.py" set ai_image.default_provider <provider>

步骤 7：问用户默认图片尺寸
   询问用户："默认图片尺寸？（推荐 2048x2048，可选 1K / 1024x1024 / 16:9 等）"
   bash: python3 "$SKILL_DIR/scripts/ai_image_config.py" set ai_image.default_size <size>

步骤 8：跑 validate 全量健康检查
   bash: python3 "$SKILL_DIR/scripts/ai_image_config.py" validate
   告知用户每个 provider 的 API key 是否就绪 / 报错原因

步骤 9：完成提示
   "ai-image 配置完成！配置文件：~/.config/presales-skills/config.yaml
    现在你可以说'生成一张 K8s 架构图'之类自然语言来生图。"
```

**关键纪律**：
- 不要批量收 API keys 后才调 set——一个一个收 + 立即写 + 立即 validate，让用户随时看到错误
- 只问用户"想配哪些 provider"，不要把 13 个全列然后挨个问（疲劳）
- 用户提供 API key 后立即写入 yaml，不要让 key 在对话历史里停留
- 用户跳过任何步骤都允许（"先这些就行"），SKILL 不强求填完所有字段

### setup 行为说明

`setup` 不直接收集 API key，行为根据 `~/.config/presales-skills/config.yaml` 与旧路径 (`~/.config/{solution-master,tender-workflow}/config.yaml`) 状态分支：

- **新 config 不存在 + 旧 config 含 api_keys** → 自动调用 migrate 合并到统一路径
- **新 config 存在但 api_keys 块为空 + 旧 config 含 api_keys** → 同样自动 migrate（防止用户跑过空 setup 后旧 ark key 永远丢）
- **新 config 不存在 + 无可迁移内容** → 写默认骨架，提示用户后续运行 `set api_keys.<provider> <key>` 填入 key
- **新 config 存在且 api_keys 已有内容** → 展示当前配置摘要

### migrate 行为说明

`migrate` 涉及备份、写 conflict 块、prune 旧 config 等高副作用操作：
- 把 `~/.config/{solution-master,tender-workflow}/config.yaml` 中的 `api_keys` / `ai_image` / `ai_keys` 三个块抽到 `~/.config/presales-skills/config.yaml`
- plugin 专属字段（cdp_sites / taa-taw / localkb 等）保留在源文件不动
- 执行前会备份原文件到 `<file>.bak.<timestamp>`

setup 已经包含 auto-migrate 兜底，正常情况下用户不需要手动调 migrate。仅在用户**已经手动跑过 setup 写了空骨架** + **后来才发现旧 config 有内容** 时，需要显式 `migrate`（auto-migrate 在已有 api_keys 时不触发）。

## 跨 plugin 调用说明

solution-master / ppt-master / tender-workflow 在自己的 SKILL.md 里调用 ai-image 时，**用同样的 installed_plugins.json bootstrap** 解析 ai-image plugin 路径（仅 plugin 名替换为 `ai-image`），然后：

```bash
python3 "$AI_IMAGE_DIR/scripts/image_gen.py" "<prompt>" --aspect_ratio 16:9 --image_size 1K -o /path/to/output/
```

模板片段（建议跨 plugin 复用）：

```bash
AI_IMAGE_DIR=$(python3 -c "
import json, os, sys
p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(p):
    d = json.load(open(p))
    for entries in d.get('plugins', {}).values():
        for e in (entries if isinstance(entries, list) else [entries]):
            if isinstance(e, dict) and '/ai-image/' in e.get('installPath', ''):
                print(e['installPath'] + '/skills/ai-image'); sys.exit(0)
" 2>/dev/null)
[ -z "$AI_IMAGE_DIR" ] && [ -n "${AI_IMAGE_PLUGIN_PATH:-}" ] && AI_IMAGE_DIR="$AI_IMAGE_PLUGIN_PATH/skills/ai-image"
[ -z "$AI_IMAGE_DIR" ] && echo "[ai-image] plugin 未安装，跳过/降级到文本占位符" >&2 && exit 0  # graceful 降级
python3 "$AI_IMAGE_DIR/scripts/image_gen.py" "<prompt>" -o /path/to/output/
```

跨 plugin 调用方按需改 `exit 0` 为 `exit 1`（强制依赖时）。

## 故障排查

- **"No image backend configured"**：运行 `python3 "$SKILL_DIR/scripts/ai_image_config.py" setup` 写默认骨架，再 `set api_keys.<provider> <key>`
- **API key 错误**：`python3 "$SKILL_DIR/scripts/ai_image_config.py" validate <provider>` 逐个核查
- **找不到 plugin**：见上方 §错误恢复 protocol——把 stderr 转述给用户并请求 `/plugin install ai-image@presales-skills`
