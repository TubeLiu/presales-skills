# Tender Workflow 全流程使用手册

> **版本**：v3.1 | **最后更新**：2026-04-07
>
> **项目地址**：https://github.com/TubeLiu/tender-workflow

---

## 目录

1. [项目介绍](#1-项目介绍)
2. [安装教程](#2-安装教程)
   - 2.1 [前置依赖](#21-前置依赖)
   - 2.2 [获取项目代码](#22-获取项目代码)
   - 2.3 [安装 Python 依赖](#23-安装-python-依赖)
   - 2.4 [确认 Skill 可用](#24-确认-skill-可用)
   - 2.5 [安装 mcp-anythingllm](#25-安装-mcp-anythingllm)
3. [API Key 配置](#3-api-key-配置)
   - 3.1 [Anthropic API Key（Claude Code）](#31-anthropic-api-keyclaude-code)
   - 3.2 [火山方舟 AI 生图配置](#32-火山方舟-ai-生图配置)
   - 3.3 [阿里云通义万相 AI 生图配置](#33-阿里云通义万相-ai-生图配置)
   - 3.4 [AnythingLLM API Key 配置](#34-anythingllm-api-key-配置)
4. [draw.io 安装教程](#4-drawio-安装教程)
5. [本地知识库构建教程](#5-本地知识库构建教程)
6. [使用教程](#6-使用教程)
   - 6.1 [tpl — 策划者（甲方）](#61-tpl--策划者甲方)
   - 6.2 [taa — 分析者（乙方）](#62-taa--分析者乙方)
   - 6.3 [taw — 撰稿者（乙方）](#63-taw--撰稿者乙方)
   - 6.4 [trv — 审核者（甲乙双方）](#64-trv--审核者甲乙双方)
   - 6.5 [twc — 统一配置管理](#65-twc--统一配置管理)
7. [全流程使用范例](#7-全流程使用范例)
8. [常见问题](#8-常见问题)
9. [免责声明](#9-免责声明)

---

## 1. 项目介绍

### 1.1 什么是 Tender Workflow

Tender Workflow 是一个**基于 Claude Code 的 AI 辅助招投标文件生成系统**。它通过四个专职 AI 角色（Skill），覆盖招投标工作的完整链路：从招标文件策划，到标书分析、内容撰写，再到最终审核。

**核心设计原则**：
- 🤖 AI 处理重复性文字工作，人负责决策与审核
- 📚 接入公司私有知识库，复用历史方案
- 🔍 实时联网搜索，获取最新产品数据
- 🔒 本地化部署，公司文档不离开本地

### 1.2 四个角色

| 角色 | 命令 | 服务对象 | 核心功能 | 状态 |
|------|------|---------|---------|------|
| 策划者 | `/tpl` | 甲方（招标方） | 将产品功能清单转换为合规的招标技术规格与评标办法，自动完成反控标处理 | ✅ v2.0 |
| 分析者 | `/taa` | 乙方（投标方） | 深度解析招标文件，生成结构化分析报告和完整投标大纲 | ✅ v2.4.0 |
| 撰稿者 | `/taw` | 乙方（投标方） | 根据大纲和知识库逐章撰写投标技术方案内容，支持并行写作、图文共生智能配图和三供应商 AI 生图 | ✅ v3.0.0 |
| 审核者 | `/trv` | 甲方+乙方 | 对招标文件、大纲、章节草稿进行多维度质量审核（大文件自动分块） | ✅ v1.4.0 |

### 1.3 典型工作流

```
【甲方视角】
产品功能清单 → /tpl → 招标技术规格与评标办法.docx

【乙方视角】
招标文件.pdf → /taa → 招标分析报告.md + 投标文件大纲.docx
                ↓
投标文件大纲.docx → /taw → 章节草稿.docx（逐章）
                ↓
章节草稿.docx → /trv → 审核报告.md（修改建议）
```

### 1.4 输出文件说明

| 命令 | 输出文件 | 保存位置 |
|------|---------|---------|
| `/tpl` | `技术规格与评标办法_<项目名>_<时间戳>.docx` | `output/tpl/` |
| `/taa` | `招标分析报告_<时间戳>.md` + `投标文件大纲_<时间戳>.docx` | `output/` |
| `/taw` | `<章节号>_<章节名>.docx` 或 `<起始>-<结束>_合并.docx` | `drafts/` |
| `/trv` | `审核报告_<类型>_<时间戳>.md` | `output/trv/` |

---

## 2. 安装教程

### 2.1 前置依赖

在开始前，请确保以下软件已安装：

#### Claude Code

Tender Workflow 基于 Claude Code 运行。

```bash
# 安装 Node.js（需 v18 或更高版本）
# macOS（使用 Homebrew）
brew install node

# Ubuntu / Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装 Claude Code
npm install -g @anthropic/claude-code

# 验证安装
claude --version
```

#### Python 3.10+

```bash
# 检查版本
python3 --version

# macOS
brew install python@3.11

# Ubuntu
sudo apt-get install python3 python3-pip
```

#### Git

```bash
git --version
# 若未安装：
# macOS: brew install git
# Ubuntu: sudo apt-get install git
```

---

### 2.2 获取项目代码

```bash
# 克隆项目到本地
git clone https://github.com/TubeLiu/tender-workflow.git

# 进入项目目录
cd tender-workflow
```

> 💡 **建议**：将项目克隆到固定目录（如 `~/projects/tender-workflow`），后续配置均基于此路径。

---

### 2.3 安装 Python 依赖

```bash
# 进入项目目录
cd ~/projects/tender-workflow

# 安装基础依赖
pip install python-docx PyYAML

# 安装 AI 生图依赖（可选，使用 --image-source ai 时需要）
pip install volcengine-python-sdk    # 火山方舟（主要）
pip install dashscope                 # 阿里云通义万相（备选）
pip install google-genai              # Google Gemini（可选）
pip install pillow                    # 图片验证（推荐）

# 安装全量依赖（一键安装上述所有包）
pip install python-docx PyYAML volcengine-python-sdk dashscope google-genai pillow
```

> ⚠️ **注意**：在部分系统上（如 Ubuntu 22.04+），需要添加 `--break-system-packages` 参数：
> ```bash
> pip install python-docx PyYAML --break-system-packages
> ```

---

### 2.4 确认 Skill 可用

本项目的 Skill 文件直接存放在 `.claude/skills/` 目录下（项目内），Claude Code 在项目目录中启动时会自动识别，**无需创建软链接**。

```bash
# 在项目目录下打开 Claude Code
cd ~/projects/tender-workflow
claude

# 在 Claude Code 会话中测试
/taa -h
/taw -h
/tpl -h
/trv -h
/twc show
```

每个命令应显示对应的帮助文档或配置信息，说明 Skill 已正确加载。

---

### 2.5 安装 mcp-anythingllm

mcp-anythingllm 是 AnythingLLM 的 MCP 工具，用于让 AI 搜索你的私有知识库。**这是可选组件**，不安装也可以正常使用本地 Local-KnowledgeBase 知识库。

#### 前置条件

1. 安装 [AnythingLLM Desktop](https://anythingllm.com/desktop)
2. 启动 AnythingLLM Desktop，确保其在运行

**验证 AnythingLLM 是否运行**：

```bash
curl http://localhost:3001/api/ping
# 预期输出：{"online":true}
```

#### 方式一：自动安装（推荐）

```bash
cd ~/projects/tender-workflow/tools/mcp-anythingllm
node install.js
```

安装脚本将自动完成：
1. 全局安装 npm 包
2. 修改 `~/.claude.json` 添加 MCP Server 配置
3. 创建 `~/.config/tender-workflow/config.yaml`
4. 交互式引导填写 API Key 和 workspace 名称

#### 方式二：手动安装

**步骤 1**：获取 AnythingLLM API Key

打开 AnythingLLM Desktop → 右上角头像 → **Settings（设置）** → **API Keys** → **Generate New API Key** → 复制生成的 Key

**步骤 2**：全局安装 npm 包

```bash
cd ~/projects/tender-workflow/tools/mcp-anythingllm
npm install -g .
```

**步骤 3**：配置 `~/.claude.json`

编辑（或创建）`~/.claude.json`，添加以下内容：

```json
{
  "mcpServers": {
    "anythingllm": {
      "command": "mcp-anythingllm",
      "args": [],
      "env": {
        "ANYTHINGLLM_BASE_URL": "http://localhost:3001",
        "ANYTHINGLLM_API_KEY": "你的-API-Key",
        "ANYTHINGLLM_WORKSPACE": "product-kb"
      }
    }
  }
}
```

> 💡 `ANYTHINGLLM_WORKSPACE` 填写你在 AnythingLLM 中创建的 workspace slug（英文小写）。

**步骤 4**：重启 Claude Code

关闭并重新打开 Claude Code，MCP 工具即可生效。

**验证**：

```bash
# 在 Claude Code 中运行
/anythingllm_list_workspaces
```

如果返回你的 workspace 列表，说明配置成功。

---

## 3. API Key 配置

### 3.1 Anthropic API Key（Claude Code）

这是使用 Claude Code 的前置条件。

```bash
# 首次启动时自动引导配置
claude

# 或手动设置
export ANTHROPIC_API_KEY="sk-ant-xxxx"

# 持久化（添加到 shell 配置文件）
echo 'export ANTHROPIC_API_KEY="sk-ant-xxxx"' >> ~/.bashrc
source ~/.bashrc
```

---

### 3.2 火山方舟 AI 生图配置

火山方舟（字节跳动）是 taw 的**默认** AI 生图提供商，支持 Seedream 5.0 Lite 模型，生成 2K-4K 高分辨率图片。

**步骤 1**：注册并获取 API Key

1. 访问 [火山方舟控制台](https://console.volcengine.com/ark)
2. 注册/登录火山引擎账号
3. 进入 **API Key 管理** → **创建 API Key**
4. 复制生成的 Key（格式：`ark-xxxx`）

**步骤 2**：配置 API Key

**方式 A：环境变量（推荐，重启失效）**

```bash
export ARK_API_KEY="ark-xxxx"
```

**方式 B：twc 命令（永久有效，推荐）**

```bash
/twc set api_keys.ark "ark-xxxx"
```

**步骤 3**：验证配置

```bash
cd ~/projects/tender-workflow
python3 ../ai-image/scripts/image_gen.py \
  --type architecture \
  --topic "容器云平台总体架构" \
  --components "基础设施层,K8s编排层,平台层" \
  --output /tmp/test_ark.png
```

成功后将生成测试图片至 `/tmp/test_ark.png`。

---

### 3.3 阿里云通义万相 AI 生图配置

阿里云通义万相（Qwen Image 2.0 Pro）是 taw 的**备选** AI 生图提供商。

**步骤 1**：获取 API Key

1. 访问 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com)
2. 登录阿里云账号
3. 进入 **API Key 管理** → **创建新的 API Key**
4. 复制生成的 Key（格式：`sk-xxxx`）

**步骤 2**：配置 API Key

```bash
# 环境变量方式
export DASHSCOPE_API_KEY="sk-xxxx"

# 或 twc 命令
/twc set api_keys.dashscope "sk-xxxx"
```

**配置文件完整示例**（`~/.config/tender-workflow/config.yaml`）：

```yaml
# 知识库路径
localkb:
  path: ~/projects/tender-workflow/Local-KnowledgeBase

# AnythingLLM（可选）
anythingllm:
  enabled: true
  workspace: product-kb

# API Keys
api_keys:
  ark: "ark-xxxx"            # 火山方舟（主要）
  dashscope: "sk-xxxx"       # 阿里云（备选）
  gemini: "xxxxx"            # Google Gemini（可选）

# AI 生图配置
ai_image:
  default_provider: ark                  # 默认供应商（ark/dashscope/gemini）
  size: 2048x2048
  models:
    ark: doubao-seedream-5-0-260128
    dashscope: qwen-image-2.0-pro
    gemini: gemini-2.5-flash-image
```

---

### 3.4 AnythingLLM API Key 配置

参见 [2.5 安装 mcp-anythingllm](#25-安装-mcp-anythingllm) 中的步骤。

已配置后，若需修改 API Key，直接编辑 `~/.claude.json`：

```json
{
  "mcpServers": {
    "anythingllm": {
      "command": "mcp-anythingllm",
      "args": [],
      "env": {
        "ANYTHINGLLM_BASE_URL": "http://localhost:3001",
        "ANYTHINGLLM_API_KEY": "新的-API-Key",
        "ANYTHINGLLM_WORKSPACE": "product-kb"
      }
    }
  }
}
```

修改后重启 Claude Code 生效。

---

## 4. draw.io 安装教程

draw.io 用于 taw 在撰写章节时自动生成专业的架构图、流程图。

### 4.1 安装 draw.io Desktop

**macOS**：

1. 访问 [draw.io 官网下载页](https://www.drawio.com/blog/diagrams-offline) 或直接下载：
   ```bash
   brew install --cask drawio
   ```
   或下载 `.dmg` 安装包后拖入 `/Applications/`

2. 验证安装路径：
   ```bash
   ls /Applications/draw.io.app/Contents/MacOS/draw.io
   # 若文件存在则说明安装成功
   ```

**Ubuntu / Linux**：

```bash
# 下载 AppImage（替换为最新版本号）
wget https://github.com/jgraph/drawio-desktop/releases/download/v24.7.8/drawio-amd64-24.7.8.AppImage
chmod +x drawio-amd64-24.7.8.AppImage
sudo mv drawio-amd64-24.7.8.AppImage /usr/local/bin/drawio
```

**Windows**：

1. 从 [draw.io GitHub Releases](https://github.com/jgraph/drawio-desktop/releases) 下载 `.exe` 安装包
2. 安装完成后，CLI 路径通常为：
   `C:\Program Files\draw.io\draw.io.exe`

### 4.2 验证 draw.io CLI

```bash
# macOS
/Applications/draw.io.app/Contents/MacOS/draw.io --version

# Linux
drawio --version
```

预期输出类似：`draw.io 24.x.x`

### 4.3 在 taw 中使用 draw.io

安装完成后，taw 会自动检测 draw.io CLI 路径，无需额外配置：

```bash
# 强制使用 draw.io 生成图表
/taw output/ --chapter 1.3 --image-source drawio

# auto 模式按 H3 子节上下文独立选择（架构/流程类优先 draw.io，产品/方案类优先 KB 图文共生）
/taw output/ --chapter 1.3 --image-source auto
```

> 💡 若 draw.io CLI 不可用，taw 会使用占位符，不影响整体流程。

---

## 5. 本地知识库构建教程

知识库是 taw 撰写高质量内容的核心，包含公司历史方案、图库和固定条款。

### 5.1 知识库目录结构

每个文档是一个独立目录，包含主文档（.md）和 `images/`（关联图片，可选），图片与文字天然绑定。索引器自动发现目录中的 .md 文件（优先匹配 `full.md`，兼容任意文件名）：

```
Local-KnowledgeBase/                          ← 独立知识库目录（路径由配置指定）
├── 技术方案-容器云解决方案/
│   ├── *.md              ← 主文档（Markdown，内嵌图片引用）
│   └── images/           ← 该文档关联的图片（可选）
│       ├── arch-01.png
│       └── flow-02.png
├── 技术方案-DevOps实施方案/
│   ├── *.md
│   └── images/
│       └── pipeline.png
├── 交付方案-售后服务条款/
│   ├── *.md
│   └── images/
└── .index/
    └── kb_catalog.yaml   ← 自动生成的目录索引
```

### 5.2 放入你的文档

将公司的技术方案、解决方案等文档转换为 Markdown 格式，放入 Local-KnowledgeBase 对应目录：

```bash
# 每个文档一个目录，包含主文档和关联图片
Local-KnowledgeBase/
├── 技术方案-容器云解决方案/
│   ├── full.md                ← 主文档（Markdown 格式）
│   └── images/                ← 文档关联的图片
│       ├── arch-01.png
│       └── flow-02.png
├── 交付方案-售后服务条款/
│   └── full.md
```

图片应放在对应文档目录的 `images/` 子目录下，并在 Markdown 文档中通过 `![](images/xxx.png)` 引用。taw 的"图文共生"机制会根据文档上下文自动匹配关联图片。

> ⚠️ **重要提示**：如果文档包含敏感客户信息，请先进行脱敏处理（替换客户名称、删除合同金额等）。

### 5.3 构建索引

文档放好后，运行索引工具让 AI 能够检索：

```bash
cd ~/projects/tender-workflow

# 生成 kb_catalog.yaml 目录索引
python3 .claude/skills/taw/tools/kb_indexer.py --scan

# 或通过 skill 触发
/taw --build-kb-index
```

索引构建完成后，会在 `Local-KnowledgeBase/.index/` 目录生成 `kb_catalog.yaml` 目录索引文件。

### 5.4 配置知识库路径

将知识库路径写入配置文件：

```bash
/twc set localkb.path ~/projects/tender-workflow/Local-KnowledgeBase
```

此命令会将路径保存到 `~/.config/tender-workflow/config.yaml`，后续无需每次指定。

### 5.5 验证知识库

```bash
# 测试知识库检索是否正常
/taw output/ --chapter 1.3 --kb-source local
```

若 AI 在生成内容时引用了知识库中的内容（会有 `[来源：local]` 标注），说明知识库配置成功。

### 5.6 使用 AnythingLLM 构建向量知识库（可选）

如果你的知识库内容很多（>50 个文档），建议使用 AnythingLLM 进行向量语义检索，效果更好：

1. 打开 AnythingLLM Desktop
2. 创建一个新 Workspace，命名如 `product-kb`
3. 上传文档（直接拖入或使用 Upload 功能）
4. 等待 AnythingLLM 完成向量化处理
5. 设置 workspace：
   ```bash
   /twc set anythingllm.workspace product-kb
   ```

---

## 6. 使用教程

> 所有命令均需在 **Claude Code 会话**中执行（即先运行 `claude`，然后在对话框中输入命令）。
> 推荐在项目根目录下启动：`cd ~/projects/tender-workflow && claude`

---

### 6.1 tpl — 策划者（甲方）

**用途**：帮助甲方将产品功能描述转换为合规的招标技术规格和评标办法，自动完成反控标处理。

#### 基本命令格式

```bash
/tpl <产品功能清单文件> --template <行业> [选项]
```

#### 参数说明

| 参数 | 必选 | 说明 |
|------|------|------|
| `<产品功能清单>` | 是* | 产品功能文件（.txt/.md/.xlsx/.pdf）|
| `--template` | 是 | 行业类型：`government`/`finance`/`soe`/`enterprise` |
| `--project <文件>` | 否 | 项目概述文件（背景、预算、规模） |
| `--level` | 否 | 细致程度（见下表，默认 `standard`） |
| `--kb` | 否 | 使用知识库产品索引替代文件输入 |
| `--no-scoring` | 否 | 只输出技术规格，跳过评标办法 |

**细致程度说明**：

| 级别 | 要求条目 | 页数 | 适用场景 |
|------|---------|------|---------|
| `detailed` | 40-60 条 | 15-20 页 | 大型项目（>500 万） |
| `standard` | 15-25 条 | 8-12 页 | 中型项目（100-500 万）**默认** |
| `general` | 8-12 条 | 4-6 页 | 小型项目（50-100 万） |
| `brief` | 5-8 条 | 2-3 页 | <50 万或内部参考 |

**行业模板说明**：

| 模板 | 适用场景 | 价格权重 | 技术权重 | 特点 |
|------|---------|---------|---------|------|
| `government` | 政府机关、事业单位 | 30% | 50% | 含信创/等保要求 |
| `finance` | 银行、保险、证券 | 25% | 50% | 金融级安全/高可用 |
| `soe` | 央国企 | 30% | 45% | 自主可控/国产化 |
| `enterprise` | 民营/外资企业 | 40% | 40% | 性价比/快速交付 |

#### 使用示例

```bash
# 最简用法：政府行业标准规格
/tpl features.txt --template government

# 金融行业，含项目背景，详细级别
/tpl features.txt --project project-overview.txt --template finance --level detailed

# 央国企，简略版，仅技术规格（不含评标办法）
/tpl features.txt --template soe --level brief --no-scoring

# 使用知识库产品索引，企业模板
/tpl --kb --template enterprise
```

#### 准备输入文件

`features.txt` 示例格式：

```
# 容器云平台功能清单

## 核心功能
- 支持 Kubernetes 1.28+ 版本集群管理
- 支持多集群统一纳管（最多 50 个集群）
- 支持 ARM 架构和 x86 架构双栈部署（控标点）
- 容器镜像仓库，支持镜像扫描和签名验证

## 运维管理
- 可视化操作界面，支持 Web 端管理
- 支持 HPA/VPA 自动弹性伸缩
...
```

> 💡 在功能条目中标注 `（控标点）` 的条目，tpl 会确保纳入招标要求且保留核心技术指标。

#### 输出文件

- `output/tpl/技术规格与评标办法_<项目名>_<时间戳>.docx`

---

### 6.2 taa — 分析者（乙方）

**用途**：深度解析招标文件，生成结构化分析报告和完整投标大纲。

#### 基本命令格式

```bash
/taa <招标文件路径> [选项]
```

#### 参数说明

| 参数 | 必选 | 说明 |
|------|------|------|
| `<招标文件>` | 是* | 招标文件（.pdf/.docx/.doc） |
| `--product <文件>` | 否 | 产品能力说明书（.xlsx/.md），用于精确评估匹配度 |
| `--vendor <名称>` | 否 | 投标厂商名称（默认"灵雀云"） |
| `--anythingllm-workspace <slug>` | 否 | 指定 AnythingLLM workspace |
| `--kb-source` | 否 | 强制知识库来源（如 `anythingllm`，不可用则报错） |
| `--build-index` | 否 | 仅构建产品索引，不执行分析 |
| `--save-index` | 否 | 分析后保存产品索引到默认位置 |

#### 使用示例

```bash
# 最简用法
/taa 招标文件.pdf

# 指定产品能力说明书（推荐，效果更准确）
/taa 招标文件.pdf --product 产品能力说明书.xlsx

# 指定厂商名称
/taa 招标文件.pdf --product 产品能力说明书.xlsx --vendor "博云"

# 使用 AnythingLLM 知识库
/taa 招标文件.pdf --anythingllm-workspace "product-kb"

# 仅构建产品索引（不做分析）
/taa --build-index --product 产品能力说明书.xlsx
```

#### 输出文件

**招标分析报告**（`output/招标分析报告_<时间戳>.md`）包含 7 个分析模块：

| 模块 | 内容 |
|------|------|
| M1 | 项目概况（背景、预算、时间节点） |
| M2 | 技术要求（逐条列出，标注【必须】/【推荐】） |
| M3 | 资质与商务要求 |
| M4 | 评分标准（各项分值） |
| M5 | 评标办法与规则 |
| M6 | 产品匹配度评估（需要 --product 参数） |
| M7 | 投标策略与差异化亮点建议 |

**投标文件大纲**（`output/投标文件大纲_<时间戳>.docx`）包含完整技术部分章节：

```
一、技术部分
  1.1 技术偏离表
  1.2 项目理解与需求分析
  1.3 总体方案设计
  1.4 [专项响应章节，根据招标要求动态生成]
  1.5 实施方案与计划
  1.6 质量保障方案
  1.7 安全方案
  1.8 国产化适配方案（如有信创要求）
  1.9 项目团队与人员配置
  1.10 售后服务方案
  1.11 培训方案
```

---

### 6.3 taw — 撰稿者（乙方）

**用途**：根据 taa 生成的大纲和分析报告，逐章撰写高质量的投标技术方案内容。

> **v3.0 新特性 — 图文共生**：taw v3.0 引入"图文共生"（text-image co-location）图片匹配模式，替代旧版的 14 条正则匹配 + 5 维度评分机制。新模式由 AI 根据段落语义自动判断是否需要配图、匹配哪张图，图片来源优先从 Local-KnowledgeBase 的文档关联图片中选取，配图上限由 `image_guidelines.yaml` 控制（章节上限 8 张、H3 上限 1 张）。

#### 基本命令格式

```bash
/taw <大纲目录或文件> --chapter <章节号> [选项]
```

#### 参数说明

| 参数 | 必选 | 说明 |
|------|------|------|
| `<目录或文件>` | 是 | taa 输出目录（或分别指定 `--outline` 和 `--report`） |
| `--chapter` | 是 | 章节号（见下文格式说明） |
| `--vendor <名称>` | 否 | 投标厂商身份（默认"灵雀云"） |
| `--kb-source` | 否 | 知识库来源：`auto`/`anythingllm`/`local`/`none` |
| `--image-source` | 否 | 图片来源：`auto`/`local`/`drawio`/`ai`/`web`/`placeholder` |
| `--image-provider` | 否 | AI 生图供应商：`ark`/`dashscope`/`gemini`（覆盖 `default_provider` 配置） |
| `--search-tool` | 否 | 搜索工具：`auto`/`mcp`/`websearch`/`tavily`/`exa` |
| `--query <词>` | 否 | 自定义搜索词 |
| `--l2-words <N>` | 否 | 二级章节（X.X 级）目标字数，覆盖模板默认值 |
| `--l3-words <N>` | 否 | 三级章节（X.X.X 级）目标字数（默认 900） |
| `--l4-words <N>` | 否 | 四级章节（X.X.X.X 级）目标字数（默认 600） |
| `--l5-words <N>` | 否 | 五级章节（X.X.X.X.X 级）目标字数（默认 400） |
| `--l2-images <N>` | 否 | 二级章节图片配额，覆盖模板默认值 |
| `--l3-images <N>` | 否 | 三级章节图片配额（默认 0） |
| `--anythingllm-workspace <slug>` | 否 | 指定 AnythingLLM workspace |
| `--build-kb-index` | 否 | 仅构建 Local-KnowledgeBase 目录索引，不执行撰写 |

#### 章节号格式

| 格式 | 示例 | 说明 |
|------|------|------|
| 整章 | `一` 或 `1` | 撰写全部 11 个子节 |
| 单节 | `1.3` | 只写第 1.3 节 |
| 范围 | `1.1-1.5` | 写第 1.1 到 1.5 节 |
| 范围（中文） | `1.1到1.9` | 同上 |
| 全部 | `all` | 写所有章节 |

#### 图片来源说明

| 参数值 | 说明 |
|--------|------|
| `auto` | **v3.0 图文共生模式**：按 H3 子节上下文独立选择图片来源——架构/流程类优先 draw.io，产品截图/历史方案类优先 KB 图文共生匹配 **默认** |
| `local` | 本地知识库图片（Local-KnowledgeBase 文档关联图片） |
| `drawio` | draw.io 生成图表（需安装 draw.io Desktop） |
| `ai` | AI 生成图片（使用默认供应商，失败时报错并使用占位符） |
| `web` | 互联网下载图片 |
| `placeholder` | 使用占位符（速度最快，后期手动插图） |

#### 使用示例

```bash
# 最简用法：撰写第 1.3 节（总体方案设计）
/taw output/ --chapter 1.3

# 指定厂商名称
/taw output/ --chapter 1.3 --vendor "博云"

# 指定文件路径（精确模式）
/taw --outline output/投标文件大纲_20260317.docx \
     --report output/招标分析报告_20260317.md \
     --chapter 1.3

# 撰写整个技术部分（全部 11 节）
/taw output/ --chapter 一

# 范围撰写（1.1 到 1.9 节）
/taw output/ --chapter 1.1到1.9

# 使用 draw.io 生成图表
/taw output/ --chapter 1.3 --image-source drawio

# 使用 AI 生图（需要 API Key，使用默认供应商）
/taw output/ --chapter 1.3 --image-source ai

# 指定 AI 生图供应商
/taw output/ --chapter 1.3 --image-source ai --image-provider gemini

# 不用知识库，纯靠互联网搜索
/taw output/ --chapter 1.3 --kb-source none

# 使用 Tavily 搜索（比 WebSearch 更精准）
/taw output/ --chapter 1.7 --search-tool tavily

# 自定义搜索词（聚焦特定技术方向）
/taw output/ --chapter 1.7 --query "等保 2.0 容器安全 零信任"

# 构建 Local-KnowledgeBase 知识库索引（v3.0 新增）
/taw --build-kb-index
```

#### 输出文件

- 单节：`drafts/1.3_总体方案设计.docx`
- 多节：`drafts/1.1-1.9_合并.docx`

---

### 6.4 trv — 审核者（甲乙双方）

**用途**：对各阶段产出物进行多维度质量审核，识别问题和风险，提供修改建议。

#### 基本命令格式

```bash
/trv <待审核文件> --type <审核类型> [选项]
```

#### 参数说明

| 参数 | 必选 | 说明 |
|------|------|------|
| `<文件>` | 是 | 待审核的文件路径 |
| `--type` | 是 | 审核类型（见下表） |
| `--reference <文件>` | 否 | 参考文件（对照审核，强烈推荐） |
| `--level` | 否 | 严格程度：`critical`/`high`/`all`（默认 `all`） |
| `--focus` | 否 | 专注维度：`completeness`/`compliance`/`scoring`/`risk` |

**审核类型说明**：

| 类型 | 审核对象 | 推荐参考文件 |
|------|---------|------------|
| `tender_doc` | tpl 生成的技术规格与评标办法 | 无（独立审核） |
| `analysis` | taa 生成的招标分析报告 | 原始招标文件 |
| `outline` | taa 生成的投标大纲 | 招标分析报告 |
| `chapter` | taw 生成的章节草稿 | 招标分析报告 |
| `full_bid` | 完整技术标书 | 原始招标文件 |

#### 审核维度说明

trv 会从以下维度进行审核（大文件分块模式下自动增加跨章节一致性检查）：

| 维度 | 检查内容 |
|------|---------|
| **完整性** | 所有技术要求和评分项是否都有响应，章节结构是否完整 |
| **合规性** | 内容是否违反招标文件规定，承诺是否合理 |
| **评分契合度** | 章节内容与评分标准的对应程度，高分项是否充分展开 |
| **风险识别** | 过度承诺、技术偏离、废标风险等 |
| **跨章节一致性** | （v1.4.0 分块模式自动启用）同一参数/承诺/描述在不同章节中是否矛盾 |

> **v1.4.0 大文件自动分块**：当标书+参考文件超过 80K token 时（如 5 万字以上的完整标书），trv 自动进入分块审核模式——按章节拆分，并行审核，最后执行跨章节一致性检查。用户无需额外操作，分块对用户透明。

#### 使用示例

```bash
# 审核 tpl 输出的技术规格（甲方用）
/trv output/tpl/技术规格与评标办法_20260317.docx --type tender_doc

# 审核 taa 输出的分析报告
/trv output/招标分析报告_20260317.md --type analysis \
    --reference 原始招标文件.pdf

# 审核投标大纲完整性
/trv output/投标文件大纲_20260317.docx --type outline \
    --reference output/招标分析报告_20260317.md

# 快速审核（只看严重问题）
/trv output/投标文件大纲_20260317.docx --type outline \
    --reference output/招标分析报告_20260317.md \
    --level critical

# 审核章节草稿，聚焦评分契合度
/trv drafts/1.3_总体方案设计.docx --type chapter \
    --reference output/招标分析报告_20260317.md \
    --focus scoring

# 审核完整标书（提交前最终检查）
/trv 完整标书.docx --type full_bid --reference 招标文件.pdf
```

#### 输出文件

- `output/trv/审核报告_<类型>_<时间戳>.md`

审核报告包含：问题清单（按严重程度排序）、修改建议、风险评估、评分预估。

> v1.4.0 分块模式下报告还包含：审核模式信息（chunk 数量、成功率）、跨章节一致性检查结果（数值矛盾、描述不一致、承诺不自洽）。

---

### 6.5 twc — 统一配置管理

**用途**：管理所有 skill 的统一配置文件（`~/.config/tender-workflow/config.yaml`），包括知识库路径、AnythingLLM、AI 生图 API、draw.io、各 skill 默认参数。

#### 基本操作

```bash
# 交互式首次配置向导（6 步引导）
/twc setup

# 查看全部配置
/twc show

# 查看特定 skill 配置（全局 + skill 专属合并视图）
/twc show taw

# 设置配置项（支持 dot notation）
/twc set localkb.path /data/company-kb
/twc set taa.vendor "博云"
/twc set tpl.default_template government
/twc set tpl.default_level detailed

# 查看可用的 AI 生图模型
/twc models              # 全部模型（三供应商）
/twc models gemini       # 仅 Gemini 模型
/twc models --refresh    # 联网搜索最新模型并更新注册表

# 健康检查（路径存在性、API 连通性、工具安装）
/twc validate

# 从旧配置迁移（~/.config/taw/ 和 ~/.config/taa/）
/twc migrate

# 重置为默认值
/twc reset
```

#### 配置文件结构

```yaml
# 全局共享
localkb:
  path: /path/to/Local-KnowledgeBase         # 知识库根目录
anythingllm:
  enabled: true
  base_url: "http://localhost:3001"
  workspace: product-kb
api_keys:
  ark: <火山方舟 API Key>
  dashscope: <阿里云 API Key>
  gemini: <Google Gemini API Key>
ai_image:
  default_provider: ark                        # 默认供应商（ark/dashscope/gemini）
  size: 2048x2048
  models:
    ark: doubao-seedream-5-0-260128
    dashscope: qwen-image-2.0-pro
    gemini: gemini-2.5-flash-image
drawio:
  cli_path: /Applications/draw.io.app/Contents/MacOS/draw.io

# Skill 专属覆盖
taa:
  vendor: 灵雀云
  kb_source: auto
taw:
  kb_source: auto
  image_source: auto
tpl:
  default_template: null
  default_level: standard
trv:
  default_level: all
```

**配置解析优先级**：CLI 参数 > 环境变量 > 统一配置(skill 节) > 统一配置(全局节) > 默认值

#### setup 向导流程

`/twc setup` 分 6 步引导完成完整配置：

1. **知识库路径** — 自动检测项目目录下的 Local-KnowledgeBase，确认或手动指定
2. **AnythingLLM** — 检查安装状态、测试连通性、选择 workspace
3. **draw.io** — 检查 skill 安装和 Desktop CLI 路径
4. **AI 生图 API Key** — 配置火山方舟/阿里云/Gemini API Key
5. **Skill 默认值** — 设置 taa 厂商名、tpl 默认模板/级别
6. **验证** — 运行健康检查，显示配置摘要

---

## 7. 全流程使用范例

以下是一个完整的投标项目实战示例。

**项目背景**：某市政务云平台采购项目，预算 300 万，要求信创适配。

### 7.1 准备工作

```bash
# 进入工作目录
cd ~/projects/tender-workflow

# 启动 Claude Code
claude

# 确认 output/ 和 drafts/ 目录存在
mkdir -p output drafts output/tpl output/trv
```

### 7.2 Step 1：分析招标文件（乙方）

```bash
# 将招标文件放入工作目录
# 假设文件名为：政务云平台招标文件.pdf

# 执行分析（指定产品说明书和厂商名）
/taa 政务云平台招标文件.pdf \
     --product 灵雀云产品能力说明书.xlsx \
     --vendor "灵雀云"
```

**等待 5-10 分钟**，AI 完成分析后输出：
- `output/招标分析报告_20260317XXXXXX.md` — 七模块结构化分析
- `output/投标文件大纲_20260317XXXXXX.docx` — 完整大纲

**人工审查**：打开分析报告，重点检查：
- M2 技术要求清单是否完整
- M6 产品匹配度评估是否准确
- M7 投标策略建议是否可行

### 7.3 Step 2：审核投标大纲（乙方）

```bash
/trv output/投标文件大纲_20260317XXXXXX.docx \
     --type outline \
     --reference output/招标分析报告_20260317XXXXXX.md
```

查看审核报告，根据建议调整大纲（直接编辑 .docx 文件）。

### 7.4 Step 3：逐章撰写技术方案（乙方）

```bash
# 先写核心章节（总体方案设计）
/taw output/ --chapter 1.3 \
     --vendor "灵雀云" \
     --image-source drawio \
     --search-tool auto

# 撰写完后审核
/trv drafts/1.3_总体方案设计.docx \
     --type chapter \
     --reference output/招标分析报告_20260317XXXXXX.md

# 根据审核意见修改，然后继续写其他章节
/taw output/ --chapter 1.2 --vendor "灵雀云"
/taw output/ --chapter 1.4 --vendor "灵雀云" --image-source drawio
/taw output/ --chapter 1.5 --vendor "灵雀云"
/taw output/ --chapter 1.6 --vendor "灵雀云"
/taw output/ --chapter 1.7 --vendor "灵雀云" --search-tool tavily
/taw output/ --chapter 1.8 --vendor "灵雀云"  # 信创适配章节
/taw output/ --chapter 1.9 --vendor "灵雀云"
/taw output/ --chapter 1.10 --vendor "灵雀云"
/taw output/ --chapter 1.11 --vendor "灵雀云"

# 或者一次性写 1.2 到 1.11 所有章节
/taw output/ --chapter 1.2到1.11 --vendor "灵雀云" --image-source auto
```

### 7.5 Step 4：提交前最终审核（乙方）

```bash
# 将所有章节合并为完整标书（手动合并 Word 文档）
# 然后整体审核
/trv 完整技术标书.docx --type full_bid --reference 政务云平台招标文件.pdf
```

根据最终审核报告，修复所有严重和高风险问题后提交。

### 7.6 甲方视角：编写招标文件（tpl）

如果你是甲方，需要编写招标技术规格：

```bash
# 准备产品功能清单（见 6.1 节格式说明）
# 假设已准备好 features.txt

# 生成政府行业标准规格
/tpl features.txt --template government --level standard

# 审核生成的招标文件
/trv output/tpl/技术规格与评标办法_20260317XXXXXX.docx --type tender_doc
```

---

## 8. 常见问题

### Q1：运行命令时提示"skill not found"

**原因**：未在项目目录中启动 Claude Code，导致 Skill 未被自动加载。

**解决方案**：
```bash
# Skill 存放在项目的 .claude/skills/ 下（非软链接），Claude Code 在项目目录中启动时会自动识别
# 确保在项目目录中启动 Claude Code
cd ~/projects/tender-workflow && claude

# 验证 Skill 目录存在
ls .claude/skills/
# 应看到 taa/ taw/ tpl/ trv/ twc/ 五个目录
```

---

### Q2：/taa 运行后无输出，或卡住不动

**原因**：招标文件过大（>100 页）或网络问题。

**解决方案**：
- 确认 Claude Code API Key 有效：`claude --version`
- 检查网络连接
- 尝试截取招标文件的核心部分（技术要求章节）单独分析

---

### Q3：/taw 生成的内容质量不好，文字很空洞

**原因**：未配置知识库，AI 缺乏公司产品具体信息。

**解决方案**：
```bash
# 1. 先构建知识库索引
/taw --build-kb-index

# 2. 配置知识库路径
/twc set localkb.path ~/projects/tender-workflow/Local-KnowledgeBase

# 3. 搭配 AnythingLLM（效果更好）
/taw output/ --chapter 1.3 --kb-source anythingllm

# 4. 使用互联网搜索补充
/taw output/ --chapter 1.3 --search-tool tavily
```

---

### Q4：AI 生图失败，图片显示为占位符

**原因**：API Key 未配置，或余额不足。

**解决方案**：
```bash
# 检查 API Key 配置
cat ~/.config/tender-workflow/config.yaml

# 测试 AI 生图是否正常
python3 ../ai-image/scripts/image_gen.py \
  --type architecture --topic "测试" --output /tmp/test.png

# 改用 draw.io（本地生成，零费用）
/taw output/ --chapter 1.3 --image-source drawio

# 或使用占位符，后期手动插图
/taw output/ --chapter 1.3 --image-source placeholder
```

---

### Q5：draw.io 图表生成失败

**原因**：draw.io Desktop 未安装，或 CLI 路径找不到。

**解决方案**：
```bash
# macOS 验证路径
ls /Applications/draw.io.app/Contents/MacOS/draw.io

# 如果不存在，重新安装 draw.io Desktop
brew install --cask drawio

# 改用 AI 生图替代
/taw output/ --chapter 1.3 --image-source ai
```

---

### Q6：AnythingLLM 搜索返回为空

**原因**：workspace 中还没有上传文档，或 workspace slug 配置错误。

**解决方案**：
```bash
# 列出所有 workspace，确认 slug
/anythingllm_list_workspaces

# 检查 Claude Code 配置
cat ~/.claude.json

# 确保 AnythingLLM Desktop 在运行
curl http://localhost:3001/api/ping
```

---

### Q7：taw 生成的章节字数不够

**原因**：知识库内容不足，AI 缺乏足够参考资料。

**解决方案**：
- 向知识库补充更多历史方案文档（放入 Local-KnowledgeBase 对应目录并重建索引）
- 使用搜索工具获取更多互联网内容：`--search-tool tavily`
- 指定更精准的搜索词：`--query "你的产品名 容器云 案例"`

---

### Q8：生成的内容包含竞争对手名称

**原因**：AI 从互联网搜索或知识库中获取了含有竞品名称的内容。

**解决方案**：
- 手动编辑输出文件，替换相关内容
- 使用 `--vendor "你的厂商名"` 参数明确指定视角
- 下次生成前在搜索词中排除竞品：`--query "产品功能 -竞品名称"`

---

### Q9：如何让 AI 以其他厂商的视角写作？

```bash
# 以博云视角写作
/taw output/ --chapter 1.3 --vendor "博云"

# 以华为云视角写作
/taw output/ --chapter 1.3 --vendor "华为云"
```

---

### Q10：生成的 Word 文档格式混乱（Markdown 标记未解析）

**原因**：`python-docx` 未安装，或版本过低。

**解决方案**：
```bash
pip install --upgrade python-docx
```

---

## 9. 免责声明

### 关于 AI 辅助工具的性质

**Tender Workflow 是一款 AI 辅助工具，旨在帮助用户提高投标文件撰写效率。它不是，也无法替代具有专业资质的投标文件撰写人员或法律顾问。**

### 用户责任

使用本工具时，用户需明确了解并接受以下事项：

1. **人工审核义务**：AI 生成的所有内容均需经过专业人员的仔细审核。投标文件的最终内容、准确性和合规性由用户负全责。**AI 是助手，人永远是决策者。**

2. **技术事实核实**：AI 通过联网搜索获取的产品参数、技术指标、案例数据等内容可能存在不准确或过时的情况，使用前必须与官方资料进行交叉核实。文档中标注有 `[来源：互联网，请核实]` 的内容尤其需要重点核查。

3. **法律合规责任**：用户有责任确保最终提交的投标文件符合《中华人民共和国招标投标法》、《政府采购法》及相关法规的要求。本工具的反控标功能旨在提供辅助，不能保证完全消除法律风险。

4. **商业敏感信息**：请勿将含有竞争对手核心商业机密、客户保密信息或法律保护数据的内容输入本工具。

5. **资质与资历**：本工具不能生成、伪造或替代法定需要企业或个人实际具备的资质证书、业绩证明、人员资历等材料。

6. **知识产权**：使用本工具生成的内容应确保不侵犯第三方知识产权。AI 引用互联网内容时，用户有责任核查其著作权状态。

### 工具局限性

- AI 的知识有截止日期，最新的政策法规、技术标准可能未被纳入训练数据
- AI 不了解你的企业实际情况、真实业绩和产品能力边界
- AI 无法预见所有评标委员会的主观评判倾向
- AI 生成的内容可能包含表述不当、逻辑不严谨等问题

### 最佳实践建议

> ✅ **推荐的使用方式**：
> - 将 AI 生成的内容作为**初稿和参考**，而非最终稿
> - 由有投标经验的售前工程师**全文审读**，对关键数据逐一核实
> - 法律相关条款（合规性、资质要求等）交由**有资质的法务人员**最终确认
> - 提交前执行**至少一轮人工 + 一轮 /trv 自动审核**

---

*本手册由项目维护者持续更新。如有问题或建议，欢迎提交 Issue 至项目 GitHub 仓库。*
