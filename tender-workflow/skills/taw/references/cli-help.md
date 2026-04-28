# taw CLI 帮助 + 完整参数

主 SKILL.md 的 §Phase 0 检测到 `-h` / `--help` 时，输出本文件 ↓ 范围内的内容并退出（不执行后续 Phase）。

```
─────────────────────────────────────────────────────
投标文件撰稿助手（taw）— 命令参数帮助
─────────────────────────────────────────────────────

用法：
  /taw --outline <大纲.docx|目录> --report <分析报告.md|目录> --chapter <章节号> [选项...]
  /taw <目录> --chapter <章节号>        # 简写：目录下自动匹配两个文件
  /taw --set-kb <知识库路径>
  /taw --build-kb-index
  /taw -h | --help

必选参数：
  --outline <文件|目录>  taa 生成的投标文件大纲（DOCX 格式）或所在目录
                         目录时取最新的 .docx 文件
                         （--set-kb / --build-kb-index / -h / --help 模式可省）
  --report <文件|目录>   taa 生成的招标分析报告（Markdown 格式）或所在目录
                         目录时取最新的 .md 文件
                         （--set-kb / --build-kb-index / -h / --help 模式可省）
  --chapter <章节号>     目标章节，支持以下格式：
                           一                    整个主章（含所有子节）
                           1.3                   单个小节
                           all                   全部章节（一、技术部分，共 11 节）
                           1.1-1.9               范围（含两端）
                           1.1到1.9 / 1.1至1.9   也支持 "到" / "至" / 空格变体

可选参数：
  --kb <路径>           临时覆盖知识库索引目录（不修改配置文件）
  --set-kb <路径>       永久设置默认知识库路径并退出
                        （保存至 ~/.config/tender-workflow/config.yaml）
  --kb-source <来源>    知识库来源：auto / local / anythingllm / none（默认 auto）
                        auto: 综合使用所有可用知识库，按匹配度动态取用
                        local: 强制使用本地 KB 目录索引，跳过 AnythingLLM
                        anythingllm: 强制使用 AnythingLLM（失败时报错）
                        none: 跳过知识库，使用互联网检索
  --image-source <来源> 图片来源：auto / local / drawio / ai / web / placeholder（默认 auto）
                        auto: 按 H3 子节上下文独立选择最合适的图片来源
                        local: 仅使用本地知识库图片（KB 图文共生）
                        drawio: 仅使用 draw.io 生成图表
                        ai: 仅使用 AI 生成图片
                        web: 仅使用互联网下载图片
                        placeholder: 仅使用占位符
  --image-provider <P>  AI 生图供应商：ark / dashscope / gemini，覆盖配置默认
                        仅当 --image-source 为 auto 或 ai 时生效
  --build-kb-index      扫描 Local-KnowledgeBase 目录生成索引并退出
                        可配合 --kb-path 指定（默认从配置读取）
  --vendor <厂商名>     指定投标厂商身份（必填，首次使用前 /twc setup 或在命令行加 --vendor）
  --query <查询词>      手工指定补充查询词，覆盖默认模板
  --search-tool <工具>  强制指定搜索工具：mcp / websearch / auto（默认 auto）
  --anythingllm-workspace <slug>
                        指定 AnythingLLM workspace slug 或名称
  --l2-words <字数>     二级章节（X.X）目标字数（覆盖模板默认值）
  --l3-words <字数>     三级章节（X.X.X）目标字数（默认 900）
  --l4-words <字数>     四级章节（X.X.X.X）目标字数（默认 600）
  --l5-words <字数>     五级章节（X.X.X.X.X）目标字数（默认 400）
  --l2-images <数量>    二级章节图片配额（覆盖模板默认值）
  --l3-images <数量>    三级章节图片配额（默认 0）
  -h, --help            显示此帮助信息并退出

示例：
  /taw output/ --chapter 1.3 --l2-words 6000 --l3-words 1200
  /taw output/ --chapter 1.3 --l2-images 3 --l3-images 1
  /taw output/ --chapter all --image-source auto
  /taw output/ --chapter 一 --kb-source none
  /taw output/ --chapter 1.3 --vendor "博云" --kb-source none
  /taw --set-kb /data/kb/index

输出：
  生产模式（推荐）：drafts/<起始节>-<结束节>_合并.docx
  单节测试模式：drafts/<章节号>_<章节名>.docx

配置文件：~/.config/tender-workflow/config.yaml
  格式：
    localkb:
      path: /path/to/Local-KnowledgeBase
    anythingllm:
      workspace: <slug-or-uuid>
─────────────────────────────────────────────────────
```

## 已废弃参数（请勿使用）

- ❌ `--strict-image` → 改用 `--image-source placeholder`
- ❌ `--no-ai-image` → 改用 `--image-source placeholder`
- ❌ `--no-kb` → 改用 `--kb-source none`
- ❌ `--image-kb` → 已废弃
- ❌ `--image-ai` → 改用 `--image-source ai`
- ❌ `--image-web` → 改用 `--image-source web`

## 章节序列

```
一 → [1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11]
```

主章别名：`一` = `1`。完整扁平序列共 11 节。
