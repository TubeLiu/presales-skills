---
description: solution-master 专属配置入口（localkb / cdp_sites / docx 选项等）。AI 图片生成的配置见 /ai-image:setup；招投标专属配置见 /twc。
---

用户运行了 `/solution-master:config $ARGUMENTS` —— 请激活 solution-master plugin 的 `solution-config` skill 处理：

`$ARGUMENTS`

详细工作流见 `skills/solution-config/SKILL.md`。

## 注意

- API keys / AI 图片生成相关配置统一由 ai-image plugin 管理（`/ai-image:setup` / `/ai-image:set` / `/ai-image:migrate`），solution-master 不再持有。
- 旧的 `/solution-config` 短名 slash 仍然可用，本命令是同一入口的 plugin namespace 版本。
