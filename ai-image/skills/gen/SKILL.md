---
name: image-gen
description: >
  AI 图片生成统一入口。覆盖 13 个后端（ark/dashscope/gemini/openai/minimax/stability/
  bfl/ideogram/zhipu/siliconflow/fal/replicate/openrouter）。
  触发：「生成图片 / 做配图 / AI 画图 / 画一张 / generate image / make illustration」（生图）；
  「PPT 配图 / 信息图 / Bento grid / UI 截图 / ER 图 / 图形摘要 / 学术配图 /
  方法流程图 / 系统架构图 / mind map」等结构化场景（自动匹配 templates/ 模板）；
  「图像编辑 / inpainting / 局部重绘 / 替换背景 / 移除元素」（仅 openai 后端，--mode edit）；
  「配置 ai-image / 初始化 / setup / reconfigure / migrate config / show config /
  validate api key / list image models / add custom model」（管理子命令，详见 SKILL.md §子命令）。
  统一读取 ~/.config/presales-skills/config.yaml 获取 API key。
  不处理视频生成或 ASCII art。
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
SKILL_DIR=$(python3 - <<'PYEOF' 2>/dev/null
import json, os, sys
p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(p):
    d = json.load(open(p))
    for entries in d.get('plugins', {}).values():
        for e in (entries if isinstance(entries, list) else [entries]):
            if isinstance(e, dict) and '/ai-image/' in e.get('installPath', ''):
                print(e['installPath'] + '/skills/gen'); sys.exit(0)
PYEOF
)

# vercel CLI fallback (skill subdir is 'gen'; SKILL.md name is 'image-gen' so vercel
# CLI installs the standalone skill at ~/.<agent>/skills/image-gen/)
[ -z "$SKILL_DIR" ] && for d in ~/.cursor/skills ~/.agents/skills .cursor/skills .agents/skills; do
    [ -d "$d/ai-image/skills/gen" ] && SKILL_DIR="$d/ai-image/skills/gen" && break
    [ -d "$d/image-gen" ] && SKILL_DIR="$d/image-gen" && break
done

# 用户预设环境变量
[ -z "$SKILL_DIR" ] && [ -n "${AI_IMAGE_PLUGIN_PATH:-}" ] && SKILL_DIR="$AI_IMAGE_PLUGIN_PATH/skills/gen"

# dev 态
[ -z "$SKILL_DIR" ] && [ -d "./ai-image/skills/gen" ] && SKILL_DIR="$(pwd)/ai-image/skills/gen"

if [ -z "$SKILL_DIR" ]; then
    echo "[ERROR] 找不到 ai-image skill 安装位置。" >&2
    echo "请设置：export AI_IMAGE_PLUGIN_PATH=/path/to/ai-image" >&2
    exit 1
fi
```

**错误恢复 protocol**：bootstrap 退出 1 时不要重试，把 stderr 转述给用户并请求 `/plugin install ai-image@presales-skills` 或手工 export 环境变量。

## 工作流（生成图片场景）

1. **读取用户意图**：图片主题、风格、尺寸、数量
2. **判断是否走模板分支**：用户描述涉及「PPT 配图 / 信息图 / Bento grid / UI 截图 / 聊天截图 / ER 图 / 系统架构图 / 流程图 / 思维导图 / 时序图 / 状态机 / 网络拓扑 / 学术图形摘要 / 神经网络架构图 / 论文图表 / 海报 / 头像 / 角色图 / 包装设计 / 漫画分镜 / 地图 / 产品图 / 字体排版」等**结构化高密度场景** → 走 §模板驱动生成；否则继续 step 3 简单生成路径
3. **选 provider**：按场景 + 用户默认偏好（来自 `~/.config/presales-skills/config.yaml` 的 `ai_image.default_provider`）
4. **准备 prompt**：如果用户只给了简要主题，扩展为详细描述
5. **执行生成**：调 `image_gen.py`：
   - 设定 `IMAGE_BACKEND` 为选定 provider 的 canonical 名（ark→volcengine，dashscope→qwen，其他同名）
   - 通过 `-o` 指定输出目录
   - 用户没显式给 size / ratio 时，分别从 `ai_image.default_size`（preset 如 `2K`）和 `ai_image.default_aspect_ratio`（比例如 `16:9`）读默认值。**两个独立参数**：size preset 决定分辨率，aspect ratio 决定形状

```bash
# 默认 provider + 默认 size + 默认 ratio（全从 config.yaml 取）
python3 "$SKILL_DIR/scripts/image_gen.py" "用户提示词" \
  --image_size "$DEFAULT_SIZE" --aspect_ratio "$DEFAULT_RATIO" -o /path/to/output/

# 显式指定 backend + size / ratio
IMAGE_BACKEND=ark python3 "$SKILL_DIR/scripts/image_gen.py" "用户提示词" \
  --image_size 2K --aspect_ratio 16:9 -o /path/to/output/
```

> ⚠ `--image_size` 只接受 preset：`512px` / `1K` / `2K` / `4K`（不是字面像素如 `2048x2048`）；
> `--aspect_ratio` 只接受 `1:1` / `16:9` / `9:16` 等比例。配置里 `default_size` 写错值，
> CLI 会被 argparse 拒，此时跑 `python3 ai_image_config.py validate` 看具体提示。

6. **验证输出**：文件存在且 > 10KB，否则降级或报错
7. **返回给用户**：图片路径 + 简要描述

## 模板驱动生成（高密度结构化场景）

`templates/` 目录提供 79 个结构化提示词模板，分 17 类，源自 [garden-skills/gpt-image-2](https://github.com/ConardLi/garden-skills)（MIT，见 `templates/LICENSE-gpt-image-2`）。每个模板用 JSON 描述视觉层结构 + `{argument name="..." default="..."}` 槽位 + 缺失字段提问优先级。

### 模板类别速查

| 类别 | 用途 | 适用主 plugin |
|---|---|---|
| `slides-and-visual-docs/` | 高密度讲解 slide / 教育 slide / 政策风 slide | ppt-master |
| `infographics/` | Bento grid / KPI dashboard / 对比信息图 / 步骤图 | solution-master / ppt-master |
| `ui-mockups/` | 聊天界面 / 短视频封面 / 直播带货 UI / 社交 UI | tender-workflow / solution-master |
| `academic-figures/` | 图形摘要 / 神经网络架构 / 论文图表 / 方法流程图 | solution-master |
| `technical-diagrams/` | ER 图 / 流程图 / 时序图 / 状态机 / 系统架构 / 网络拓扑（PNG，非矢量；可编辑用 drawio）| solution-master |
| `infographics/` `maps/` `poster-and-campaigns/` `product-visuals/` `branding-and-packaging/` `portraits-and-characters/` `avatars-and-profile/` `editing-workflows/` `grids-and-collages/` `scenes-and-illustrations/` `storyboards-and-sequences/` `typography-and-text-layout/` `assets-and-props/` | 海报 / 地图 / 产品图 / 头像 / 漫画 / 等 | 通用 |

### 模板匹配工作流

```
T1. 用 Grep / find 在 $SKILL_DIR/templates/ 下找类别 → 文件
    例：用户要"PPT 配图，4 块 Bento grid 信息图" → templates/infographics/bento-grid-infographic.md

T2. Read 模板文件，重点读"## 缺失信息优先提问顺序"或"参数策略"小节
    → 找出 must-ask 字段（必须问用户）和 defaultable 字段（可用默认）

T3. 按 must-ask 列表向用户提问（一次问完，避免反复打断）

T4. 把模板里的 JSON prompt 块拷贝出来，逐个替换 {argument name="..."} 占位符
    → 得到一个填好的 JSON

T5. 把这段 JSON 整体当 prompt 字符串传给 image_gen.py
    （JSON 不需要"展开"成自然语言；模型能直接解析结构化 JSON prompt）

T6. 标准 generate 流程（同 §工作流 step 5-7）
```

### 模板调用范例

```bash
# 假设 T4 已得到填好的 JSON 字符串保存在 /tmp/prompt.txt
PROMPT=$(cat /tmp/prompt.txt)
IMAGE_BACKEND=ark python3 "$SKILL_DIR/scripts/image_gen.py" "$PROMPT" \
  --image_size 2K --aspect_ratio 3:4 -o /path/to/output/
```

> 💡 **provider 选择提示**：模板里多含中文文字层时优先 dashscope（中文渲染最稳）；
> 学术图 / 技术图（强调结构清晰度）优先 ark / openai；纯英文 UI mockup 用 gemini / openai。
> ER 图 / 系统架构图等"工程图"场景，如果用户接受可编辑矢量，**优先 drawio plugin** 而非本插件。

### Provider 选择策略

| 用户场景 | 推荐 provider |
|---|---|
| 中文场景、文字渲染（图表/海报）| `dashscope` (qwen-image-2.0-pro) |
| 真实感照片、高分辨率 | `ark` (Seedream 4.5 / 5.0) |
| 通用画质、英文场景 | `gemini` (2.5 Flash Image) |
| 聚合平台、多模型切换 | `openrouter` / `fal` / `replicate` |

详细列表：`python3 "$SKILL_DIR/scripts/ai_image_config.py" models`

## OpenAI 高级参数（透明背景 / 输出格式）

仅 `IMAGE_BACKEND=openai` 生效，其他后端会忽略：

| 参数 | 取值 | 用途 |
|---|---|---|
| `--background` | `auto` / `transparent` / `opaque` | logo / icon 抠图：`transparent` 强制 PNG |
| `--output-format` | `png` / `jpeg` / `webp` | 控制输出文件格式 |
| `--output-compression` | `0-100` | 仅对 jpeg / webp 生效，控制体积 |

```bash
# 透明背景 PNG（logo / icon 场景）
IMAGE_BACKEND=openai python3 "$SKILL_DIR/scripts/image_gen.py" "logo of a fox, vector style" \
  --background transparent --aspect_ratio 1:1 -o /path/to/output/

# webp 输出 + 高压缩（节省体积）
IMAGE_BACKEND=openai python3 "$SKILL_DIR/scripts/image_gen.py" "background landscape" \
  --output-format webp --output-compression 85 -o /path/to/output/
```

## 图像编辑（Inpainting）

仅 `IMAGE_BACKEND=openai` 支持。给定原始图像 PNG 与可选 mask，执行局部或整图重绘。

| 参数 | 必填 | 说明 |
|---|---|---|
| `--mode edit` | 是 | 切换到编辑模式（默认 `generate`）|
| `--input-image` | 是 | 原图 PNG 路径 |
| `--mask` | 否 | mask PNG 路径：透明=待编辑区域，不透明=保留；省略则全图重绘 |
| `--input-fidelity` | 否 | `low` / `high`（默认 `high`，越高越保留原图） |

```bash
# 全图编辑（无 mask）
IMAGE_BACKEND=openai python3 "$SKILL_DIR/scripts/image_gen.py" \
  "添加一只橘猫坐在窗边" \
  --mode edit --input-image /path/to/photo.png \
  --input-fidelity high -o /path/to/output/

# Inpainting（带 mask）
IMAGE_BACKEND=openai python3 "$SKILL_DIR/scripts/image_gen.py" \
  "替换为蓝天白云" \
  --mode edit --input-image /path/to/photo.png --mask /path/to/sky_mask.png \
  -o /path/to/output/
```

## 配置

完整 setup wizard 见同目录 [`setup.md`](setup.md)。**当用户说「配置 ai-image / 帮我配置 ai-image / 初始化 / setup / migrate / 我刚装新版需要配置」时**：

1. 用 Read 工具加载 `$SKILL_DIR/setup.md`（路径 `$SKILL_DIR` 由 §路径自定位 段解析）
2. 严格按 setup.md 引导用户完成配置（含 Python 依赖前置检查、API key 收集 + 立即实测、默认模型 / 默认 provider / 默认尺寸 选择）
3. 不要凭记忆执行 — 每次都 Read 当前版本

### 命令速查（已熟悉的 power user 直接用）

所有配置通过 `ai_image_config.py` 子命令。先按 §路径自定位 解析 `SKILL_DIR`：

| 子命令 | 命令 |
|---|---|
| setup（含 auto-migrate） | `python3 "$SKILL_DIR/scripts/ai_image_config.py" setup` |
| show | `python3 "$SKILL_DIR/scripts/ai_image_config.py" show [section]` |
| set | `python3 "$SKILL_DIR/scripts/ai_image_config.py" set <key.path> <value>` |
| models | `python3 "$SKILL_DIR/scripts/ai_image_config.py" models [provider]` |
| add-model | `python3 "$SKILL_DIR/scripts/ai_image_config.py" add-model <provider> <yaml>` |
| validate | `python3 "$SKILL_DIR/scripts/ai_image_config.py" validate [provider]` |
| migrate（手动；setup 已含 auto-migrate） | `python3 "$SKILL_DIR/scripts/ai_image_config.py" migrate` |

### setup auto-migrate 逻辑（仅供参考，详见 setup.md）

`setup` 不直接收集 API key，根据 `~/.config/presales-skills/config.yaml` 与旧路径状态分支：

- 新 config 不存在 + 旧 config 含 api_keys → **自动调 migrate** 合并到统一路径
- 新 config 存在但 api_keys 为空 + 旧 config 有内容 → **同样自动 migrate**（防止用户跑过空 setup 后旧 key 永远丢）
- 新 config 不存在 + 无可迁移 → 写默认骨架
- 新 config 存在且 api_keys 已有内容 → 展示摘要

setup.md wizard 已经处理这些分支 + 引导后续填 key + 选默认模型 + 实测验证。

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
                print(e['installPath'] + '/skills/gen'); sys.exit(0)
" 2>/dev/null)
[ -z "$AI_IMAGE_DIR" ] && [ -n "${AI_IMAGE_PLUGIN_PATH:-}" ] && AI_IMAGE_DIR="$AI_IMAGE_PLUGIN_PATH/skills/gen"
[ -z "$AI_IMAGE_DIR" ] && echo "[ai-image] plugin 未安装，跳过/降级到文本占位符" >&2 && exit 0  # graceful 降级
python3 "$AI_IMAGE_DIR/scripts/image_gen.py" "<prompt>" -o /path/to/output/
```

跨 plugin 调用方按需改 `exit 0` 为 `exit 1`（强制依赖时）。

## 故障排查

- **"No image backend configured"**：运行 `python3 "$SKILL_DIR/scripts/ai_image_config.py" setup` 写默认骨架，再 `set api_keys.<provider> <key>`
- **API key 错误**：`python3 "$SKILL_DIR/scripts/ai_image_config.py" validate <provider>` 逐个核查
- **找不到 plugin**：见上方 §错误恢复 protocol——把 stderr 转述给用户并请求 `/plugin install ai-image@presales-skills`
