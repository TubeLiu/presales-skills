#!/usr/bin/env bash
# presales-skills v1.0.0 cache cleanup
#
# 清理 v0.x 旧 mega-skill cache，避免与 v1.0.0 split / 物理改名后的新 sub-skill ID 冲突。
#
# 背景：Claude Code `/plugin update` 不会自动清理旧版 cache，导致升级到 v1.0.0 后
# 旧 mega ID（如 /ai-image:ai-image, /drawio:drawio, /ppt-master:ppt-master）与
# 新 ID（/ai-image:gen, /drawio:draw, /ppt-master:make）同时显示在 available skills，
# 造成 slash 自动补全混乱。本脚本仅删 0.[0-4].x 旧版本 cache，保留 1.x 当前版本。
#
# 使用：
#   bash ~/.claude/plugins/cache/presales-skills/<latest-version>/bin/clean-stale-cache.sh
# 或本地源码：
#   bash bin/clean-stale-cache.sh

set -e

CACHE="$HOME/.claude/plugins/cache/presales-skills"

if [ ! -d "$CACHE" ]; then
    echo "✓ 无 presales-skills cache 目录，无需清理 ($CACHE 不存在)"
    exit 0
fi

removed=0
# 仅清 5 个 v1.0.0 改 mega-skill 形态的 plugin。
# anythingllm-mcp + tender-workflow 在 v1.0.0 不动 dir 形态（前者无 SKILL.md，
# 后者已是 5 sub-skill 结构），其旧 cache 不会与新版本产生 ID 冲突。
for plugin in ai-image drawio ppt-master solution-master web-access; do
    plugin_cache="$CACHE/$plugin"
    [ -d "$plugin_cache" ] || continue
    for old_ver in "$plugin_cache"/0.[0-4]*; do
        if [ -d "$old_ver" ]; then
            echo "✗ Removing $old_ver"
            rm -rf "$old_ver"
            removed=$((removed + 1))
        fi
    done
done

if [ "$removed" -eq 0 ]; then
    echo "✓ 无 v0.x 旧版本 cache 残留，无需清理。"
else
    echo ""
    echo "✓ 已清理 $removed 个 v0.x 旧版本 cache 目录。"
    echo "  请重启 Claude Code 让 /plugin 注册表刷新。"
fi
