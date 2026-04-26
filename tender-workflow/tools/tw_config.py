#!/usr/bin/env python3
"""DEPRECATED shim — v1.1.0 移除。真实实现已迁移到 skills/twc/tools/tw_config.py。

兼容老用户脚本与文档（README:439、CLAUDE.md:99-103 历史宣传过 `python3 tools/tw_config.py ...`
作为公开 CLI 入口）。直接 transparently 转发到新路径，sys.argv 共享。
"""
import os
import runpy
import sys

print(
    "[tender-workflow] WARN: tools/tw_config.py 已迁移到 skills/twc/tools/tw_config.py。"
    " 本 shim 在 v1.1.0 移除，请更新调用路径。",
    file=sys.stderr,
)
runpy.run_path(
    os.path.join(os.path.dirname(__file__), "..", "skills", "twc", "tools", "tw_config.py"),
    run_name="__main__",
)
