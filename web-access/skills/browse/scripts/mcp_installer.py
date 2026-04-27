#!/usr/bin/env python3
"""MCP wizard 工具：检测 runtime / 自动装 / 探活 / 注册 MCP server / 实测 tool 调用。

被 tender-workflow / solution-master 的 setup wizard 调用，也可单独 CLI 使用。

支持的 MCP server：
  - tavily            (npm: tavily-mcp@latest)         环境变量: TAVILY_API_KEY
  - exa               (npm: exa-mcp-server@latest)     环境变量: EXA_API_KEY
  - minimax           (uv:  minimax-coding-plan-mcp)   环境变量: MINIMAX_API_KEY (sk-cp- 前缀)
                                                                + MINIMAX_API_HOST

CLI 用法：
    python3 mcp_installer.py check <node|uv>
    python3 mcp_installer.py auto-install <node|uv>
    python3 mcp_installer.py probe <tavily|exa|minimax>
    python3 mcp_installer.py register <provider> --key=<KEY> [--host=<HOST>] [--dry-run]
    python3 mcp_installer.py test <provider> [--key=<KEY>] [--host=<HOST>]
    python3 mcp_installer.py unregister <provider>
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

CLAUDE_JSON = Path.home() / ".claude.json"
DEFAULT_MINIMAX_HOST = "https://api.minimaxi.com"
# 国内稳定可达的公开图（百度首页 logo），用于 minimax understand_image 实测
STABLE_IMG_URL = "https://www.baidu.com/img/PCtm_d9c8750bed0b3c7d089fa7d55720d6cf.png"

# ── MCP server 注册模板（写到 ~/.claude.json 的 mcpServers）──
TEMPLATES = {
    "tavily": {
        "command": "npx",
        "args": ["-y", "tavily-mcp@latest"],
        "env": {"TAVILY_API_KEY": ""},
    },
    "exa": {
        "command": "npx",
        "args": ["-y", "exa-mcp-server@latest"],
        "env": {"EXA_API_KEY": ""},
    },
    "minimax": {
        "command": "uvx",
        "args": ["minimax-coding-plan-mcp", "-y"],
        "env": {"MINIMAX_API_KEY": "", "MINIMAX_API_HOST": DEFAULT_MINIMAX_HOST},
    },
}

KEY_ENV = {"tavily": "TAVILY_API_KEY", "exa": "EXA_API_KEY", "minimax": "MINIMAX_API_KEY"}

# 探活命令（只验证 runtime + 包能下/启动；不真调 tool）
PROBE_CMDS = {
    "tavily":  ["npx", "-y", "tavily-mcp@latest", "--version"],
    "exa":     ["npx", "-y", "exa-mcp-server@latest", "--help"],
    "minimax": ["uvx", "minimax-coding-plan-mcp", "-y", "--help"],
}

# 实测 tool/call 矩阵（test 子命令用）
TEST_CALLS = {
    "tavily":  [("tavily_search", {"query": "kubernetes", "max_results": 1})],
    "exa":     [("exa_search", {"query": "kubernetes"})],
    "minimax": [
        ("web_search", {"query": "hello"}),
        ("understand_image", {"prompt": "请简要描述这张图。", "image_url": STABLE_IMG_URL}),
    ],
}


# ════════════════════════════════════════════════════════
# subprocess 工具
# ════════════════════════════════════════════════════════

def _resolve_cmd(cmd: list[str]) -> list[str]:
    """把 cmd[0] 解析成 shutil.which 找到的真实可执行文件路径。

    Windows 上 npx/uvx 是 .cmd 文件，Python subprocess (shell=False) 不走 PATHEXT，
    直接传字符串会报 WinError 2。shutil.which 会查 PATHEXT 找到 npx.cmd，把 cmd[0]
    替换成绝对路径后 subprocess 即可正常 spawn。

    若 which 找不到（runtime 真缺）→ 保留原 cmd[0]，让 subprocess 抛 FileNotFoundError，
    由调用方走 NEEDS_USER_ACTION / FAIL 分支。
    """
    if not cmd:
        return cmd
    resolved = shutil.which(cmd[0])
    if resolved:
        return [resolved] + list(cmd[1:])
    return cmd


# ════════════════════════════════════════════════════════
# check / auto-install
# ════════════════════════════════════════════════════════

def cmd_check(runtime: str) -> int:
    if runtime not in ("node", "uv"):
        print(f"unknown runtime: {runtime}", file=sys.stderr)
        return 2
    binary = {"node": "node", "uv": "uv"}[runtime]
    path = shutil.which(binary)
    if path:
        print(f"OK {path}")
        return 0
    print("MISSING")
    return 1


def cmd_auto_install(runtime: str) -> int:
    """用户级（无 sudo）安装为主；落到 sudo 时输出 NEEDS_USER_ACTION 让 setup.md 转发。"""
    if runtime == "uv":
        return _install_uv()
    if runtime == "node":
        return _install_node()
    print(f"unknown runtime: {runtime}", file=sys.stderr)
    return 2


def _install_uv() -> int:
    if sys.platform == "win32":
        cmd = ["powershell", "-NoProfile", "-Command",
               "irm https://astral.sh/uv/install.ps1 | iex"]
        note = "安装到 %USERPROFILE%\\.local\\bin，需 reopen shell 让 PATH 生效"
    else:
        cmd = ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"]
        note = "安装到 ~/.local/bin（或 ~/.cargo/bin），需 reopen shell 让 PATH 生效"
    return _run_install(cmd, "uv", note)


def _install_node() -> int:
    """优先用户级 (fnm)，回落系统包管理器（macOS brew / Win winget 都不要 sudo）"""
    cmd: Optional[list[str]] = None
    label = ""
    if shutil.which("fnm"):
        cmd, label = (["fnm", "install", "22"], "fnm install 22")
    elif shutil.which("brew"):
        cmd, label = (["brew", "install", "node@22"], "brew install node@22")
    elif shutil.which("winget"):
        cmd, label = (["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS"],
                      "winget install OpenJS.NodeJS.LTS")
    elif sys.platform == "win32":
        # 既无 winget 又无 fnm — 让用户去装
        print("NEEDS_USER_ACTION: 未检测到 winget / fnm。请先装 Node.js 22+：")
        print("  下载：https://nodejs.org/")
        return 1
    else:
        # Unix 兜底：用户级装 fnm
        cmd, label = (["sh", "-c", "curl -fsSL https://fnm.vercel.app/install.sh | bash"],
                      "curl fnm install.sh | bash → fnm install 22")
    return _run_install(cmd, "node", note=f"通过 {label}；如装的是 fnm，仍需 fnm install 22 + 重开 shell")


def _run_install(cmd: list[str], name: str, note: str = "") -> int:
    try:
        r = subprocess.run(cmd, timeout=600)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"NEEDS_USER_ACTION: 自动安装 {name} 失败 ({e})。请手动执行：")
        print(f"  {' '.join(cmd)}")
        return 1
    if r.returncode == 0:
        print(f"OK {name} 安装完成")
        if note:
            print(f"NOTE: {note}")
        return 0
    print(f"NEEDS_USER_ACTION: 自动安装 {name} 退出码 {r.returncode}。请手动执行：")
    print(f"  {' '.join(cmd)}")
    return 1


# ════════════════════════════════════════════════════════
# probe
# ════════════════════════════════════════════════════════

def cmd_probe(provider: str, timeout: int = 120) -> int:
    if provider not in PROBE_CMDS:
        print(f"unknown provider: {provider}", file=sys.stderr)
        return 2
    cmd = _resolve_cmd(PROBE_CMDS[provider])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        print(f"FAIL {provider}: runtime missing ({e})")
        return 1
    except subprocess.TimeoutExpired:
        print(f"FAIL {provider}: timeout {timeout}s")
        return 1
    if r.returncode == 0:
        print(f"PASS {provider}")
        return 0
    err = (r.stderr or r.stdout or "").strip().splitlines()
    last = err[-1] if err else "(no output)"
    print(f"FAIL {provider}: {last[:200]}")
    return 1


# ════════════════════════════════════════════════════════
# register / unregister
# ════════════════════════════════════════════════════════

def build_server_config(provider: str, key: str, host: Optional[str] = None) -> dict:
    """构造写入 ~/.claude.json mcpServers.<provider> 的 dict。

    minimax 强制要求 sk-cp- 前缀（issue #96：普通 chat key 拿来做 MCP 会报 invalid api key）。
    """
    if provider not in TEMPLATES:
        raise ValueError(f"unknown provider: {provider}")
    if provider == "minimax" and not key.startswith("sk-cp-"):
        raise ValueError("INVALID_KEY_PREFIX: minimax key must start with 'sk-cp-' (Token Plan 专属 key)")
    cfg = json.loads(json.dumps(TEMPLATES[provider]))
    cfg["env"][KEY_ENV[provider]] = key
    if provider == "minimax":
        cfg["env"]["MINIMAX_API_HOST"] = host or DEFAULT_MINIMAX_HOST
    return cfg


def cmd_register(provider: str, key: str, host: Optional[str], dry_run: bool) -> int:
    try:
        server_cfg = build_server_config(provider, key, host)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    if dry_run:
        print(json.dumps({provider: server_cfg}, indent=2, ensure_ascii=False))
        return 0
    try:
        cfg = read_claude_json()
    except ClaudeJsonCorrupted as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3
    if CLAUDE_JSON.exists():
        bak = CLAUDE_JSON.with_suffix(f".json.bak.{int(time.time())}")
        try:
            shutil.copy2(CLAUDE_JSON, bak)
        except OSError as e:
            print(f"WARN: backup to {bak} failed: {e}", file=sys.stderr)
    cfg.setdefault("mcpServers", {})[provider] = server_cfg
    write_claude_json(cfg)
    print(f"OK {provider} written to {CLAUDE_JSON}")
    print("NOTE: 需 /reload-plugins 或重启 Claude Code 才在主 session 生效；"
          "test 子命令独立起 server 不受影响")
    return 0


def cmd_unregister(provider: str) -> int:
    try:
        cfg = read_claude_json()
    except ClaudeJsonCorrupted as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3
    servers = cfg.get("mcpServers", {})
    if provider not in servers:
        print(f"OK {provider} not in mcpServers (already absent)")
        return 0
    del servers[provider]
    write_claude_json(cfg)
    print(f"OK {provider} removed from {CLAUDE_JSON}")
    return 0


class ClaudeJsonCorrupted(RuntimeError):
    """~/.claude.json 损坏抛此异常，由 caller 决策（不在 read_claude_json 里 sys.exit
    避免 setup wizard 中途强退、丢失 runtime 安装等已完成的副作用状态）。"""


def read_claude_json() -> dict:
    if not CLAUDE_JSON.exists():
        return {}
    try:
        return json.loads(CLAUDE_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ClaudeJsonCorrupted(
            f"~/.claude.json 解析失败 ({e})。请先修复（用编辑器打开校正 JSON 语法），"
            f"避免覆盖丢数据；修好后重新跑本命令。"
        ) from e


def write_claude_json(cfg: dict) -> None:
    CLAUDE_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = CLAUDE_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    for attempt in range(3):
        try:
            tmp.replace(CLAUDE_JSON)
            break
        except PermissionError:
            if attempt == 2:
                raise
            time.sleep(0.1)
    # 含三 provider API key 明文，最低权限保护（同机多用户可见性）
    # 失败时仅 stderr warn（Windows NTFS / FAT / SMB 等非 POSIX 文件系统常见）
    try:
        os.chmod(CLAUDE_JSON, 0o600)
    except OSError as e:
        sys.stderr.write(
            f"[mcp_installer] WARN: chmod 0600 failed on {CLAUDE_JSON}: {e}\n"
            f"  ~/.claude.json 含 API keys 明文，但权限保护未启用（同机多用户可见）。\n"
        )


# ════════════════════════════════════════════════════════
# test: stdio JSON-RPC client + tools/call
# ════════════════════════════════════════════════════════

def cmd_test(provider: str, key: Optional[str], host: Optional[str]) -> int:
    """spawn MCP server via stdio, JSON-RPC handshake, tools/call 实测矩阵。

    不依赖 reload-plugins —— 在主 session 写完 ~/.claude.json 之后立即可调，
    与主 session 的 MCP server 生命周期完全独立。
    """
    if provider not in TEMPLATES:
        print(f"unknown provider: {provider}", file=sys.stderr)
        return 2
    # key 取来源：CLI > ~/.claude.json
    if not key:
        try:
            srv = read_claude_json().get("mcpServers", {}).get(provider, {})
        except ClaudeJsonCorrupted as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 3
        env = srv.get("env", {})
        key = env.get(KEY_ENV[provider])
        if not host and provider == "minimax":
            host = env.get("MINIMAX_API_HOST")
    if not key:
        print(f"FAIL {provider}: no key (传 --key 或先 register)", file=sys.stderr)
        return 1
    try:
        server_cfg = build_server_config(provider, key, host)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    cmd = _resolve_cmd([server_cfg["command"]] + server_cfg["args"])
    env = {**os.environ, **server_cfg["env"]}

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as e:
        print(f"FAIL {provider}: cannot spawn server: {e}")
        return 1

    out_q: queue.Queue = queue.Queue()
    err_buf: list[str] = []

    def _read_stdout() -> None:
        for line in iter(proc.stdout.readline, ""):
            out_q.put(line)
        out_q.put(None)

    def _read_stderr() -> None:
        for line in iter(proc.stderr.readline, ""):
            err_buf.append(line)
            if len(err_buf) > 200:
                err_buf.pop(0)

    threading.Thread(target=_read_stdout, daemon=True).start()
    threading.Thread(target=_read_stderr, daemon=True).start()

    overall_ok = True
    try:
        send_jsonrpc(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05",
                       "capabilities": {},
                       "clientInfo": {"name": "mcp_installer", "version": "1.0.0"}},
        })
        init = recv_jsonrpc(out_q, expected_id=1, timeout=60)
        if init.get("error"):
            print(f"FAIL {provider}: initialize: {init['error']}")
            return 1
        send_jsonrpc(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        for i, (tool, args) in enumerate(TEST_CALLS[provider], start=2):
            send_jsonrpc(proc, {
                "jsonrpc": "2.0", "id": i, "method": "tools/call",
                "params": {"name": tool, "arguments": args},
            })
            try:
                resp = recv_jsonrpc(out_q, expected_id=i, timeout=90)
            except TimeoutError as e:
                print(f"FAIL {tool}: {e}")
                overall_ok = False
                continue
            if resp.get("error"):
                print(f"FAIL {tool}: {resp['error']}")
                overall_ok = False
            elif resp.get("result", {}).get("isError"):
                content = resp.get("result", {}).get("content", [])
                msg = content[0].get("text", "") if content and isinstance(content, list) else ""
                print(f"FAIL {tool}: {msg[:200] or '(server returned isError)'}")
                overall_ok = False
            else:
                print(f"PASS {tool}")
    except (TimeoutError, RuntimeError) as e:
        print(f"FAIL {provider}: {e}")
        if err_buf:
            tail = "".join(err_buf[-5:]).strip()
            print(f"  stderr tail: {tail[:300]}")
        overall_ok = False
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    return 0 if overall_ok else 1


def send_jsonrpc(proc: subprocess.Popen, msg: dict) -> None:
    """单行 JSON 写入 stdin（MCP stdio = newline-delimited JSON）。"""
    line = json.dumps(msg, ensure_ascii=False) + "\n"
    if proc.stdin is None:
        raise RuntimeError("server stdin closed")
    proc.stdin.write(line)
    proc.stdin.flush()


def recv_jsonrpc(q: queue.Queue, expected_id: int, timeout: float) -> dict:
    """从 reader thread 队列里捞匹配 id 的 response；忽略 notification / log 行。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            line = q.get(timeout=max(0.05, deadline - time.time()))
        except queue.Empty:
            continue
        if line is None:
            raise RuntimeError("server stdout closed (server crashed?)")
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            # 非 JSON 行（log）跳过
            continue
        if msg.get("id") == expected_id:
            return msg
        # 其他 id / notification → 跳过继续等
    raise TimeoutError(f"no response to id={expected_id} in {timeout}s")


# ════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════

def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sp = p.add_subparsers(dest="cmd", required=True)

    sub = sp.add_parser("check"); sub.add_argument("runtime")
    sub = sp.add_parser("auto-install"); sub.add_argument("runtime")
    sub = sp.add_parser("probe"); sub.add_argument("provider")
    sub = sp.add_parser("register")
    sub.add_argument("provider")
    sub.add_argument("--key", required=True)
    sub.add_argument("--host", default=None)
    sub.add_argument("--dry-run", action="store_true")
    sub = sp.add_parser("test")
    sub.add_argument("provider")
    sub.add_argument("--key", default=None)
    sub.add_argument("--host", default=None)
    sub = sp.add_parser("unregister"); sub.add_argument("provider")

    a = p.parse_args()
    if a.cmd == "check":         return cmd_check(a.runtime)
    if a.cmd == "auto-install":  return cmd_auto_install(a.runtime)
    if a.cmd == "probe":         return cmd_probe(a.provider)
    if a.cmd == "register":      return cmd_register(a.provider, a.key, a.host, a.dry_run)
    if a.cmd == "test":          return cmd_test(a.provider, a.key, a.host)
    if a.cmd == "unregister":    return cmd_unregister(a.provider)
    return 2


if __name__ == "__main__":
    sys.exit(main())
