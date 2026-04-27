# ai-image 配置 wizard

> 触发自 ai-image SKILL.md 的 §配置 段。本文件由 Claude 在用户说「配置 ai-image / 帮我配置 ai-image / 初始化 ai-image / setup ai-image / 我刚装新版」时 Read 加载。
>
> **关键纪律**：
> 1. 每次都 Read 当前版本——不要凭记忆执行
> 2. **从步骤 0 开始一路走到步骤 6**——不论 ai_image_config.py setup 命令输出"已写骨架 / 已迁移 / 配置已存在 + 摘要"哪一种，wizard 流程不变，没有"配置已存在 → 只展示摘要"的快捷分支

## 步骤 0：开场询问（实测开关）（必问，不可跳过；配置已存在也要问）

询问用户：

> "开始之前先确认一件事：要不要每配完一个 provider 立即生一张测试图（512x512，约 <0.01 USD/张）来验证 key 真的能用？默认开。说"跳过实测"可整体关闭。"

记录用户选择为 SKIP_TEST=true / false（默认 false）。

> **关键纪律**：必须问，不能跳过。**即使下面步骤 1 的 setup 命令输出"配置已存在 + 摘要"，也要先问这个**——已有配置不代表 key 还能用（可能过期 / 余额耗尽 / 模型下架）。本 wizard 的目的就是确认"现在能不能生图"，而不是"配置文件里有没有字段"。
>
> 反检查：如果你正考虑因为"看起来已经配好了"而跳到展示摘要，停下来——这正是 wizard 最常见的脱轨模式。

## 步骤 0.5：依赖前置检查（Python ≥ 3.10）

```bash
python3 --version 2>/dev/null || python --version 2>/dev/null || py -3 --version 2>/dev/null
```

- ✅ 已装且版本 ≥ 3.10 → 继续步骤 1
- ⚠ Windows 特例：命令"成功"但**无任何输出**（exit code 49）= WindowsApps 下的 Microsoft Store stub（`%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe` 未真正安装 Python，只会弹商店）。把它当成"未装"处理，进入下方依赖安装引导。识别方式：
  ```bash
  python --version 2>&1 | grep -qi "Microsoft Store" && echo STUB
  where python 2>&1 | grep -qi "WindowsApps" && echo STUB
  ```
- ❌ 未装 / 版本 < 3.10 / Store stub：进入下方"依赖安装引导"

### 依赖安装引导

1. **检测平台 + 包管理器**：
   ```bash
   uname -s   # Darwin / Linux / MINGW* / MSYS_NT*
   command -v brew >/dev/null && echo HAS_BREW
   command -v winget >/dev/null && echo HAS_WINGET
   command -v apt >/dev/null && echo HAS_APT
   command -v dnf >/dev/null && echo HAS_DNF
   ```

2. **走非 sudo 路径（Claude 直接执行）**：
   - macOS（已装 brew）→ 准备命令 `brew install python@3.11`
   - Windows（已装 winget）→ 准备命令 `winget install -e --id Python.Python.3.11`

3. **走 sudo 路径（Claude 不能跑，仅打印让用户复制到自己 terminal）**：
   - Debian/Ubuntu → 打印 `sudo apt install python3 python3-pip`
   - RHEL/Fedora → 打印 `sudo dnf install python3 python3-pip`

4. **非 sudo 路径执行前必须先告诉用户**：

   > "我想为你执行 `<完整命令>`，需要你确认。这会装 Python 3.11 到 `<预期路径>`，无需 sudo。要继续吗？(y/n)"

   收到 y 才用 Bash 工具执行；收到 n 或没明确同意 → 停下来告知"装好后回话告诉我'装好了'，我重新检测"。

5. **装完重新跑步骤 0.5 的检测命令**，确认 ≥3.10 才继续步骤 1。

## 步骤 1：解析 SKILL_DIR + 跑 setup（含 auto-migrate）

按 SKILL.md §路径自定位 段解析 SKILL_DIR 后：

```bash
python3 "$SKILL_DIR/scripts/ai_image_config.py" setup
```

读 stdout / stderr 告知用户结果（已迁移 / 已写骨架 / 配置已存在 + 摘要）。

> **关键纪律**：不论 setup 输出哪种结果（已迁移 / 已写骨架 / 配置已存在），**都继续按步骤 2 → 3 → 3.4 实测 → 4 → 5 → 6 走完完整 wizard 流程**。"配置已存在"不是跳出 wizard 的信号——它只是告诉你不需要重写骨架；后续步骤的目的（让用户决定要不要改 key、要不要换默认模型、要不要实测）都仍然有效。

## 步骤 2：展示当前配置

```bash
python3 "$SKILL_DIR/scripts/ai_image_config.py" show api_keys
```

让用户看到当前哪些 provider 已经有 key。

## 步骤 3：循环 — 选 provider → 配 key → 选默认模型 → 实测（核心）

询问用户：

> "你想配置哪些 AI 图片 provider？我推荐先配以下几个常用的：
> - ark（火山方舟，Seedream 4.5/5.0，真实感照片）
> - dashscope（阿里云通义万相，中文场景 / 文字渲染）
> - gemini（Google Gemini 2.5 Flash Image，通用画质）
>
> 你也可以选 13 个 provider 中的任意一个或多个：openai / minimax / stability / bfl / ideogram / zhipu / siliconflow / fal / replicate / openrouter
>
> 请告诉我**先配哪一个 provider 名 + 它的 API key**。"

收到第一个 provider + key 后进入循环（每轮 5-6 步）：

### 3.1 写入 key

```bash
python3 "$SKILL_DIR/scripts/ai_image_config.py" set api_keys.<provider> <key>
```

### 3.2 列该 provider 的可选模型

```bash
python3 "$SKILL_DIR/scripts/ai_image_config.py" models <provider>
```

把表格展示给用户。

### 3.3 让用户为该 provider 选默认模型（必做，不可跳过）

在 3.2 列出的模型表格基础上，明确告诉用户：

> "我需要为 `<provider>` 选一个默认模型——以后跑生图时，如果用户没显式指定模型，就用这个默认。
>
> 表格里有 `<N>` 个模型，我推荐选 `<最常用的 model_id>`（理由：`<速度/质量/价格平衡 / 中文最强 / 真实感最好 / etc>`）。
>
> 你可以直接同意我的推荐，也可以从表里挑别的。"

收到用户选择后写入：

```bash
python3 "$SKILL_DIR/scripts/ai_image_config.py" set ai_image.models.<provider> <model_id>
```

> **关键纪律**：必须问，不能跳过。每个 provider 都有自己适合的默认模型——后续 `image_gen.py` 用 `IMAGE_BACKEND=<provider>` 调用时如果没指定 model，会回到 `ai_image.models.<provider>` 字段查找；该字段为空时只能用 provider 注册表的全局 fallback，往往不是用户想要的。

### 3.4 实测（如步骤 0 SKIP_TEST=false）

**关键：在用户原 cwd 生成测试图（不是 /tmp）**：

```bash
# 不要 cd，保持当前 cwd 即可（cwd 应已在用户工作目录）
pwd   # 让用户看到测试图会落在哪
# 用 canonical preset 512px（各 backend 都能识别），别用 WxH 字面量（部分 backend 只认 preset）
IMAGE_BACKEND=<provider> python3 "$SKILL_DIR/scripts/image_gen.py" \
  "a red apple" --aspect_ratio 1:1 --image_size 512px \
  -o "./ai-image-test-<provider>"
```

告知用户：

> "已在当前目录 `<pwd>` 生成 `./ai-image-test-<provider>.png`，用 `<model_id>` 测试。请打开看一眼是不是正常（应该是一只红苹果）。如果图损坏 / 报错，告诉我具体错误。"

### 3.5 实测结果分支

- ✅ 用户确认 OK → 步骤 3.6
- ❌ 实测失败 / 图错：把 `image_gen.py` 的 stderr 转述给用户。常见原因：
  - key 无效 / 格式错 → 让用户重新提供 key 走 3.1
  - 余额不足 → 提示用户充值后重试
  - 网络阻塞 → 提示用户检查 VPN / 防火墙
  - 模型不可用 → 让用户从 `models` 表挑别的模型走 3.3

  让用户决定：set 一个新 key 重试 / 换模型 / 先标记 broken 跳过。

### 3.6 问下一个 provider

> "还要配下一个 provider 吗？"

- 用户给下一个 provider + key → 回到 3.1
- 用户说"不要了" / "够了" → 退出循环到步骤 4

## 步骤 4：默认 provider（已配多个时）

如果步骤 3 配了多个 provider，问：

> "默认用哪个 provider 作为生图后端？（推荐 `<第一个测通的>`）"

```bash
python3 "$SKILL_DIR/scripts/ai_image_config.py" set ai_image.default_provider <provider>
```

如果只配了 1 个 provider，自动用它作为 default：

```bash
python3 "$SKILL_DIR/scripts/ai_image_config.py" set ai_image.default_provider <唯一的 provider>
```

## 步骤 5：默认图片尺寸 + 长宽比（拆两问，必做）

> **背景**：`image_gen.py` 把"尺寸"分两个独立参数：
> - `--image_size` 只接受 **preset**：`512px` / `1K` / `2K` / `4K`（决定分辨率）
> - `--aspect_ratio` 只接受 **比例**：`1:1` / `16:9` / `9:16` 等（决定形状）
>
> 早期版本把这俩混问、还接受字面像素值 — 全是错的（CLI argparse 拒）。这一步必须拆两问。

### 5.1 默认 size preset（按已配 default model 的上限过滤候选）

先读 step 4 写入的 `ai_image.default_provider`，再读该 provider 在 step 3.3 写入的 default model，
查询该 model 的 `max_resolution` 算出可选 preset 范围：

```bash
python3 -c "
import sys, json
sys.path.insert(0, '$SKILL_DIR/scripts')
import ai_image_config as ac
cfg = ac.load_config() or {}
ai = cfg.get('ai_image', {})
prov = ai.get('default_provider')
model = (ai.get('models') or {}).get(prov)
if not prov or not model:
    print(json.dumps({'supported': ac.ALL_IMAGE_SIZES, 'reason': 'no default model yet'}))
else:
    sizes = ac.supported_sizes_for_model(prov, model)
    print(json.dumps({'provider': prov, 'model': model, 'supported': sizes,
                      'max': sizes[-1] if sizes else None}))
"
```

把输出展示给用户：

> "default_provider = `<prov>`，default model = `<model>`。该 model 最大支持 `<max>`，
> 可选 preset：`<supported>`。
>
> 默认 image_size 选哪个？（推荐 `<max>`——榨干 model 能力）"

收到用户选择后**校验在 supported 列表里**，再写入：

```bash
# 用户选了 supported 中的某个 preset（如 2K）
python3 "$SKILL_DIR/scripts/ai_image_config.py" set ai_image.default_size <preset>
```

> **关键纪律**：必须按 model max 过滤候选——不能让用户选超出 model 能力的 preset
> （否则生图时被 model 拒，用户体验最差）。如果用户配多个 provider，**这里只看 default_provider 的 default model**；
> 跑生图时切到别的 provider，CLI 会用各 backend 自己的 size 适配逻辑。

### 5.2 默认 aspect ratio

> "默认 aspect_ratio 选哪个？常用：
>   - `16:9` — PPT / 横版示意图（推荐）
>   - `1:1` — 头像 / 方图
>   - `9:16` — 手机竖版 / 海报
>   - 其它见 `ALL_ASPECT_RATIOS`：1:4 / 1:8 / 2:3 / 3:2 / 3:4 / 4:1 / 4:3 / 4:5 / 5:4 / 8:1 / 21:9"

收到用户选择后写入：

```bash
python3 "$SKILL_DIR/scripts/ai_image_config.py" set ai_image.default_aspect_ratio <ratio>
```

## 步骤 6：全量 validate + 完成提示

```bash
python3 "$SKILL_DIR/scripts/ai_image_config.py" validate
```

告知用户每个 provider 的 API key 字段是否就绪 + 实测覆盖了哪几个。

完成提示：

> "ai-image 配置完成！配置文件：`~/.config/presales-skills/config.yaml`
>
> 现在你可以说"生成一张 K8s 架构图"之类自然语言来生图。
>
> 测试图保留在你当前目录，不需要可手动删除：`rm ./ai-image-test-*.png`"

## 关键纪律

- **步骤 0 实测开关必问 — 配置已存在不是跳过本步的理由**（最常见的 wizard 脱轨模式：AI 看到"配置已存在"就合理化为"展示摘要即可"，自行缩短工作流）
- 一步一问 + 立即写入 + 立即验证（不批量收答案）
- 用户跳过任何"可选"字段都允许，但**默认模型必须选**（步骤 3.3 不可跳）
- 实测失败不要默默跳过——必须转述错误让用户决策
- API key 不在对话历史里停留——立即写入 yaml
- 测试图必须落在用户当前 `cwd`，不要 `/tmp`
- **不论用户的初始触发是"配置 / 初始化 / 我刚装新版 / setup ai-image"哪一种，也不论 ai_image_config.py setup 输出"已迁移 / 已写骨架 / 配置已存在 + 摘要"哪一种，都从步骤 0 开始走完整 wizard**——本文件没有"快捷查看"分支，看到 setup 输出"配置已存在"就停在摘要 = 脱轨
