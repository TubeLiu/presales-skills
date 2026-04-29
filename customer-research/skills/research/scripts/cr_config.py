#!/usr/bin/env python3
"""
Customer Research 配置管理工具

配置文件：~/.config/presales-skills/config.yaml（customer_research 段）

CLI 用法：
    python3 cr_config.py show                          # 显示当前配置
    python3 cr_config.py get <key> [default]            # 读取单个值
    python3 cr_config.py set <key> <value>              # 写入单个值
    python3 cr_config.py setup                          # 交互式首次配置
"""

import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    import subprocess
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyyaml", "-q"],
        )
    except subprocess.CalledProcessError:
        print("错误：缺少 pyyaml 依赖且自动安装失败，请手动执行：", file=sys.stderr)
        print(f"  {sys.executable} -m pip install pyyaml", file=sys.stderr)
        sys.exit(1)
    import yaml

CONFIG_PATH = Path.home() / ".config" / "presales-skills" / "config.yaml"

SECTION = "customer_research"

DEFAULTS = {
    "user_company": "",
}


def _read_yaml(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"警告：配置文件解析失败 {path}: {e}", file=sys.stderr)
        return {}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_path.replace(path)


def get_section(data: dict) -> dict:
    """获取 customer_research 段，不存在则返回默认值。"""
    section = data.get(SECTION, {})
    if not isinstance(section, dict):
        section = {}
    merged = {**DEFAULTS, **section}
    return merged


def cmd_show():
    data = _read_yaml(CONFIG_PATH)
    section = get_section(data)
    print(f"配置文件：{CONFIG_PATH}")
    print(f"{SECTION}:")
    for k, v in section.items():
        display_v = v if v else "(未设置)"
        print(f"  {k}: {display_v}")


def cmd_get(key: str, default: str = ""):
    data = _read_yaml(CONFIG_PATH)
    section = get_section(data)
    value = section.get(key, default)
    print(value)


def cmd_set(key: str, value: str):
    data = _read_yaml(CONFIG_PATH)
    if SECTION not in data or not isinstance(data.get(SECTION), dict):
        data[SECTION] = {}
    data[SECTION][key] = value
    _write_yaml(CONFIG_PATH, data)
    print(f"已设置 {SECTION}.{key} = {value}")


def cmd_setup():
    """交互式首次配置。"""
    data = _read_yaml(CONFIG_PATH)
    section = get_section(data)
    current = section.get("user_company", "")

    if current:
        print(f"当前用户企业：{current}")
        ans = input("是否更换？直接回车保留，或输入新的企业名称：").strip()
        if not ans:
            print("保持不变。")
            return
        name = ans
    else:
        name = input("您所在的企业名称是哪家？（您自己的公司）：").strip()
        if not name:
            print("未输入，跳过配置。")
            return

    if SECTION not in data or not isinstance(data.get(SECTION), dict):
        data[SECTION] = {}
    data[SECTION]["user_company"] = name
    _write_yaml(CONFIG_PATH, data)
    print(f"已设置用户企业：{name}")


def main():
    if len(sys.argv) < 2:
        print("用法：python3 cr_config.py <show|get|set|setup> [args...]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "show":
        cmd_show()
    elif cmd == "get":
        if len(sys.argv) < 3:
            print("用法：python3 cr_config.py get <key> [default]", file=sys.stderr)
            sys.exit(1)
        key = sys.argv[2]
        default = sys.argv[3] if len(sys.argv) > 3 else ""
        cmd_get(key, default)
    elif cmd == "set":
        if len(sys.argv) < 4:
            print("用法：python3 cr_config.py set <key> <value>", file=sys.stderr)
            sys.exit(1)
        cmd_set(sys.argv[2], sys.argv[3])
    elif cmd == "setup":
        cmd_setup()
    else:
        print(f"未知命令：{cmd}", file=sys.stderr)
        print("可用命令：show, get, set, setup", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
