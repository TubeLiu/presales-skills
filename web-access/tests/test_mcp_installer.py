"""mcp_installer.py 单元测试

不依赖联网、不真起 server、不真写 ~/.claude.json（用 monkeypatch 重定向）。
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "browse" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import mcp_installer as mi  # noqa: E402


# ════════════════════════════════════════════════════════
# 1. TEMPLATES / KEY_ENV / PROBE_CMDS / TEST_CALLS 完整性
# ════════════════════════════════════════════════════════

def test_templates_cover_three_providers():
    assert set(mi.TEMPLATES.keys()) == {"tavily", "exa", "minimax"}


def test_each_template_has_required_env_key():
    for provider, env_key in mi.KEY_ENV.items():
        assert env_key in mi.TEMPLATES[provider]["env"], f"{provider} 缺 {env_key}"


def test_minimax_template_has_host_default():
    env = mi.TEMPLATES["minimax"]["env"]
    assert env["MINIMAX_API_HOST"] == mi.DEFAULT_MINIMAX_HOST


def test_minimax_test_calls_both_tools():
    """minimax test 必须同时跑 web_search + understand_image，不能漏。"""
    tools = [t for t, _ in mi.TEST_CALLS["minimax"]]
    assert "web_search" in tools
    assert "understand_image" in tools
    assert len(tools) == 2


def test_understand_image_uses_stable_url():
    args = dict(mi.TEST_CALLS["minimax"])["understand_image"]
    assert args["image_url"] == mi.STABLE_IMG_URL
    assert args["image_url"].startswith("https://")


def test_probe_cmds_match_templates():
    assert set(mi.PROBE_CMDS.keys()) == set(mi.TEMPLATES.keys())


def test_test_calls_match_templates():
    assert set(mi.TEST_CALLS.keys()) == set(mi.TEMPLATES.keys())


# ════════════════════════════════════════════════════════
# 2. build_server_config: sk-cp- 校验 + 字段填充
# ════════════════════════════════════════════════════════

def test_minimax_rejects_non_sk_cp_key():
    with pytest.raises(ValueError, match="sk-cp-"):
        mi.build_server_config("minimax", "wrong-prefix-key")


def test_minimax_accepts_sk_cp_key():
    cfg = mi.build_server_config("minimax", "sk-cp-abc123")
    assert cfg["env"]["MINIMAX_API_KEY"] == "sk-cp-abc123"
    assert cfg["env"]["MINIMAX_API_HOST"] == mi.DEFAULT_MINIMAX_HOST


def test_minimax_custom_host_override():
    cfg = mi.build_server_config("minimax", "sk-cp-x", host="https://other.example.com")
    assert cfg["env"]["MINIMAX_API_HOST"] == "https://other.example.com"


def test_tavily_accepts_arbitrary_key():
    cfg = mi.build_server_config("tavily", "anything-goes")
    assert cfg["env"]["TAVILY_API_KEY"] == "anything-goes"


def test_exa_accepts_arbitrary_key():
    cfg = mi.build_server_config("exa", "exa-whatever")
    assert cfg["env"]["EXA_API_KEY"] == "exa-whatever"


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="unknown provider"):
        mi.build_server_config("doesnotexist", "k")


def test_build_does_not_mutate_template():
    """build_server_config 必须 deepcopy，避免污染全局 TEMPLATES。"""
    before = json.dumps(mi.TEMPLATES["minimax"])
    mi.build_server_config("minimax", "sk-cp-mutate-test")
    after = json.dumps(mi.TEMPLATES["minimax"])
    assert before == after


# ════════════════════════════════════════════════════════
# 3. cmd_register: atomic write 不损坏既有 mcpServers + 顶层字段
# ════════════════════════════════════════════════════════

@pytest.fixture
def fake_claude_json(tmp_path, monkeypatch):
    fake = tmp_path / ".claude.json"
    pre = {
        "mcpServers": {
            "preexisting": {"command": "noop", "args": [], "env": {}},
        },
        "otherTopLevel": {"keep": "this"},
    }
    fake.write_text(json.dumps(pre), encoding="utf-8")
    monkeypatch.setattr(mi, "CLAUDE_JSON", fake)
    return fake


def test_register_preserves_other_mcp_servers(fake_claude_json):
    rc = mi.cmd_register("tavily", "tvly-x", host=None, dry_run=False)
    assert rc == 0
    cfg = json.loads(fake_claude_json.read_text())
    assert "preexisting" in cfg["mcpServers"]
    assert cfg["mcpServers"]["tavily"]["env"]["TAVILY_API_KEY"] == "tvly-x"


def test_register_preserves_other_top_level_fields(fake_claude_json):
    mi.cmd_register("exa", "exa-key", host=None, dry_run=False)
    cfg = json.loads(fake_claude_json.read_text())
    assert cfg["otherTopLevel"] == {"keep": "this"}


def test_register_creates_backup(fake_claude_json, tmp_path):
    mi.cmd_register("tavily", "tvly-y", host=None, dry_run=False)
    baks = list(tmp_path.glob(".claude.json.bak.*"))
    assert len(baks) == 1


def test_register_dry_run_does_not_touch_file(fake_claude_json, tmp_path):
    before = fake_claude_json.read_text()
    rc = mi.cmd_register("tavily", "tvly-dry", host=None, dry_run=True)
    assert rc == 0
    after = fake_claude_json.read_text()
    assert before == after
    assert not list(tmp_path.glob(".claude.json.bak.*"))


def test_register_minimax_invalid_prefix_returns_2(fake_claude_json):
    rc = mi.cmd_register("minimax", "wrong", host=None, dry_run=True)
    assert rc == 2
    # 文件不应被改
    cfg = json.loads(fake_claude_json.read_text())
    assert "minimax" not in cfg["mcpServers"]


def test_register_into_empty_claude_json(tmp_path, monkeypatch):
    fake = tmp_path / ".claude.json"  # 不存在
    monkeypatch.setattr(mi, "CLAUDE_JSON", fake)
    rc = mi.cmd_register("tavily", "tvly-z", host=None, dry_run=False)
    assert rc == 0
    cfg = json.loads(fake.read_text())
    assert cfg["mcpServers"]["tavily"]["env"]["TAVILY_API_KEY"] == "tvly-z"


# ════════════════════════════════════════════════════════
# 4. cmd_unregister 行为
# ════════════════════════════════════════════════════════

def test_unregister_removes_target_only(fake_claude_json):
    mi.cmd_register("tavily", "tvly-1", host=None, dry_run=False)
    rc = mi.cmd_unregister("tavily")
    assert rc == 0
    cfg = json.loads(fake_claude_json.read_text())
    assert "tavily" not in cfg["mcpServers"]
    assert "preexisting" in cfg["mcpServers"]


def test_unregister_absent_is_idempotent(fake_claude_json):
    rc = mi.cmd_unregister("nonexistent")
    assert rc == 0


# ════════════════════════════════════════════════════════
# 5. auto-install 命令矩阵决策（mock platform / which）
# ════════════════════════════════════════════════════════

def _capture_run(captured: dict):
    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)
    return fake_run


def test_install_uv_unix_curl_install(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(subprocess, "run", _capture_run(captured))
    assert mi._install_uv() == 0
    assert "astral.sh/uv/install.sh" in " ".join(captured["cmd"])


def test_install_uv_windows_powershell(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "run", _capture_run(captured))
    assert mi._install_uv() == 0
    assert any("install.ps1" in c for c in captured["cmd"])
    assert captured["cmd"][0] == "powershell"


def test_install_node_prefers_fnm(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(mi.shutil, "which",
                        lambda name: "/usr/local/bin/fnm" if name == "fnm" else None)
    monkeypatch.setattr(subprocess, "run", _capture_run(captured))
    assert mi._install_node() == 0
    assert captured["cmd"][0] == "fnm"


def test_install_node_falls_back_to_brew(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(mi.shutil, "which",
                        lambda name: "/usr/local/bin/brew" if name == "brew" else None)
    monkeypatch.setattr(subprocess, "run", _capture_run(captured))
    assert mi._install_node() == 0
    assert captured["cmd"][0] == "brew"


def test_install_node_unix_no_pkg_mgr_uses_fnm_curl(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(mi.shutil, "which", lambda name: None)
    monkeypatch.setattr(subprocess, "run", _capture_run(captured))
    assert mi._install_node() == 0
    assert "fnm.vercel.app" in " ".join(captured["cmd"])


# ════════════════════════════════════════════════════════
# 6. JSON-RPC frame send / recv (MCP stdio = newline-delimited JSON)
# ════════════════════════════════════════════════════════

class _FakeProc:
    def __init__(self):
        self.lines: list[str] = []
        self.stdin = self

    def write(self, line):
        self.lines.append(line)

    def flush(self):
        pass


def test_send_jsonrpc_appends_newline():
    proc = _FakeProc()
    mi.send_jsonrpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "ping"})
    assert proc.lines[-1].endswith("\n")
    parsed = json.loads(proc.lines[-1])
    assert parsed == {"jsonrpc": "2.0", "id": 1, "method": "ping"}


def test_recv_jsonrpc_matches_id_skipping_others():
    q: queue.Queue = queue.Queue()
    q.put('{"jsonrpc":"2.0","method":"notif","params":{}}\n')
    q.put('{"jsonrpc":"2.0","id":2,"result":"other"}\n')
    q.put('{"jsonrpc":"2.0","id":1,"result":"ok"}\n')
    msg = mi.recv_jsonrpc(q, expected_id=1, timeout=2)
    assert msg["result"] == "ok"


def test_recv_jsonrpc_skips_non_json_log_lines():
    q: queue.Queue = queue.Queue()
    q.put("[INFO] some log line not JSON\n")
    q.put('{"jsonrpc":"2.0","id":1,"result":"ok"}\n')
    msg = mi.recv_jsonrpc(q, expected_id=1, timeout=2)
    assert msg["result"] == "ok"


def test_recv_jsonrpc_eof_raises_runtime_error():
    q: queue.Queue = queue.Queue()
    q.put(None)
    with pytest.raises(RuntimeError, match="closed"):
        mi.recv_jsonrpc(q, expected_id=1, timeout=2)


def test_recv_jsonrpc_timeout_raises():
    q: queue.Queue = queue.Queue()
    with pytest.raises(TimeoutError):
        mi.recv_jsonrpc(q, expected_id=1, timeout=0.3)


# ════════════════════════════════════════════════════════
# 7. cmd_check 行为
# ════════════════════════════════════════════════════════

def test_check_unknown_runtime():
    assert mi.cmd_check("python") == 2


def test_check_node_present(monkeypatch, capsys):
    monkeypatch.setattr(mi.shutil, "which",
                        lambda name: "/opt/homebrew/bin/node" if name == "node" else None)
    assert mi.cmd_check("node") == 0
    out = capsys.readouterr().out
    assert out.startswith("OK ")


def test_check_uv_missing(monkeypatch, capsys):
    monkeypatch.setattr(mi.shutil, "which", lambda name: None)
    assert mi.cmd_check("uv") == 1
    assert "MISSING" in capsys.readouterr().out
