---
name: ai-image
description: AI 图片生成统一入口。当用户说"生成图片"、"AI 画图"、"generate image"、"做配图"、"生成一张插图"或明确指定某个 provider（ark/gemini/openai/...）时触发。支持 13 个后端（volcengine/ark、qwen/dashscope、gemini、openai、minimax、stability、bfl、ideogram、zhipu、siliconflow、fal、replicate、openrouter），统一读取 ~/.config/presales-skills/config.yaml 获取 API key。配置管理使用 /ai-image-config 子命令系列。
---

# ai-image Skill — 统一 AI 图片生成

ai-image 是 presales-skills marketplace 的共享 plugin，为 solution-master / ppt-master / tender-workflow 三个主 plugin 提供统一的图片生成能力。

## 如何调用

### 跨 plugin 调用方推荐用法（solution-master / ppt-master / tender-workflow 跨 plugin 调用走此风格）

```bash
# YAML 注册表风格（默认 provider 来自 ~/.config/presales-skills/config.yaml）
image-gen "用户提示词" --aspect_ratio 16:9 --image_size 1K -o /path/to/output/

# env-var 风格（显式指定 backend）
IMAGE_BACKEND=ark image-gen "用户提示词" -o /path/to/output/
```

`image-gen` 是 ai-image plugin 的 `bin/` 入口（`/reload-plugins` 后自动上 PATH），跨 plugin 必须走此命令——参见下方 §跨 plugin 调用说明。

### 插件内部直接调用（仅 ai-image 自家维护脚本时使用，不推荐外部消费方）

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/image_gen.py "用户提示词" --aspect_ratio 16:9 --image_size 1K -o /path/to/output/
```

> ⚠ 外部 plugin 不能复制此风格——`${CLAUDE_SKILL_DIR}` 在它们的 SKILL 里指向各自的 skill 目录而非 ai-image。跨 plugin 必须走 `image-gen` bin 命令。

### Provider 选择策略

| 用户场景 | 推荐 provider |
|---|---|
| 中文场景、文字渲染（图表/海报）| `dashscope` (qwen-image-2.0-pro) |
| 真实感照片、高分辨率 | `ark` (Seedream 4.5 / 5.0) |
| 通用画质、英文场景 | `gemini` (2.5 Flash Image) |
| 聚合平台、多模型切换 | `openrouter` / `fal` / `replicate` |

详细列表：`/ai-image:models`

## 工作流

1. **读取用户意图**：图片主题、风格、尺寸、数量
2. **选 provider**：按场景 + 用户默认偏好（来自 `~/.config/presales-skills/config.yaml` 的 `ai_image.default_provider`）
3. **准备 prompt**：如果用户只给了简要主题，扩展为详细描述
4. **执行生成**：调 `image_gen.py`，确保：
   - 设定 `IMAGE_BACKEND` 为选定 provider 的 canonical 名（ark→volcengine，dashscope→qwen，其他同名）
   - 通过 `-o` 指定输出目录
   - 根据 `ai_image.default_size` 或用户显式指定的 aspect ratio / size
5. **验证输出**：文件存在且 > 10KB，否则降级或报错
6. **返回给用户**：图片路径 + 简要描述

## 配置管理

所有配置通过 /ai-image:* 子命令系列管理（每个 subcommand 是独立 slash command）：

| 子命令 | 作用 |
|---|---|
| `/ai-image:setup` | 交互式首次配置 |
| `/ai-image:show` | 展示当前配置（API keys 自动 mask）|
| `/ai-image:set` | 按 dotted path 设值 |
| `/ai-image:models` | 展示统一注册表（13 provider）|
| `/ai-image:add-model` | 追加用户自定义模型 |
| `/ai-image:validate` | 健康检查（API key 是否已配置）|
| `/ai-image:migrate` | 合并旧的 solution-master / tender-workflow config |

## 跨 plugin 调用说明（PATH + bin/ 机制）

solution-master / ppt-master / tender-workflow 在各自 SKILL.md 里通过 **bin/ 注入的 PATH 命令** 调用本 plugin——不是路径引用：

```bash
# 生成图片（调 bin/image-gen，wrapper 自定位 scripts/image_gen.py）
image-gen "<prompt>" --aspect_ratio 16:9 --image_size 1K -o /path/to/output/

# 配置管理（调 bin/ai-image-config，wrapper 自定位 scripts/ai_image_config.py）
ai-image-config models
ai-image-config set api_keys.ark <key>
```

**详见上方 §跨 plugin 调用方推荐用法 vs §插件内部直接调用 的对比。**

**为什么用 bin/ 而不是 `${CLAUDE_PLUGIN_ROOT}/../ai-image/scripts/...` 相对路径**：

`${CLAUDE_PLUGIN_ROOT}` 在本地 marketplace 和远程（GitHub）marketplace 下结构不同：
- 本地：`<monorepo>/<plugin>/` → `..` 到 monorepo 根，`../ai-image/scripts/` 正确
- 远程：`~/.claude/plugins/cache/<mp>/<plugin>/<version>/` → `..` 只到版本父目录，`../ai-image/scripts/` 会落到 `<plugin>/ai-image/scripts/`（不存在）

bin/ wrapper 通过 `BASH_SOURCE` 自定位脚本目录，跟缓存布局无关；且 Claude Code 自动把每个 plugin 的 `bin/` 加到 PATH，调用方**按命令名调用即可**。这是跨 plugin 架构最稳健的模式，Milestone E 完整验证过。

## 故障排查

- **"No image backend configured"**：运行 `/ai-image:setup`
- **"drawio plugin 未安装"等跨 plugin 引用失败**：检查 umbrella marketplace 是否装齐所有依赖 plugin
- **API key 错误**：`/ai-image:validate <provider>` 逐个核查
