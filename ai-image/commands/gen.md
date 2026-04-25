---
description: AI 图片生成主入口（等价自然语言"生成图片"或 /image-gen skill）。接受 prompt + 可选参数，直接生图。
---

用户运行了 `/ai-image:gen $ARGUMENTS` —— 请按 ai-image plugin 的 `image-gen` skill 流程为用户生成图片。

**用户输入**：`$ARGUMENTS`

## 执行步骤

1. **解析意图**：从 `$ARGUMENTS` 中提取主题、风格、尺寸、provider 等线索；缺失项询问或用默认。
2. **选 provider**：参考 `~/.config/presales-skills/config.yaml` 的 `ai_image.default_provider`；中文/文字图优先 `dashscope`，真实感优先 `ark`，通用 `gemini`。详见 `/ai-image:models`。
3. **生成 prompt**：用户只给了简要主题时扩写为详细描述。
4. **调用 bin**：
   ```bash
   image-gen "<prompt>" --aspect_ratio 16:9 --image_size 1K -o <output_dir>
   ```
   或显式指定 backend：`IMAGE_BACKEND=ark image-gen ...`
5. **验证输出**：文件存在且 > 10KB，否则降级或报错。
6. **返回**：图片路径 + 一行描述。

## 前置检查

如果 `~/.config/presales-skills/config.yaml` 不存在或没有可用 API key，先引导用户跑 `/ai-image:setup`，再来 `/ai-image:gen`。

## 配置管理

`/ai-image:setup | show | set | models | add-model | validate | migrate` 详见各自 slash 命令。
