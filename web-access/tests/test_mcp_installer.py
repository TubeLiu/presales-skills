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


# ════════════════════════════════════════════════════════
# 8. read_claude_json 损坏 → 抛 ClaudeJsonCorrupted（不再 sys.exit）
# ════════════════════════════════════════════════════════

def test_read_claude_json_corrupted_raises(tmp_path, monkeypatch):
    fake = tmp_path / ".claude.json"
    fake.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(mi, "CLAUDE_JSON", fake)
    with pytest.raises(mi.ClaudeJsonCorrupted, match="解析失败"):
        mi.read_claude_json()


def test_read_claude_json_missing_returns_empty(tmp_path, monkeypatch):
    fake = tmp_path / ".claude.json"  # 不存在
    monkeypatch.setattr(mi, "CLAUDE_JSON", fake)
    assert mi.read_claude_json() == {}


def test_register_returns_3_on_corrupt_claude_json(tmp_path, monkeypatch, capsys):
    fake = tmp_path / ".claude.json"
    fake.write_text("garbage{", encoding="utf-8")
    monkeypatch.setattr(mi, "CLAUDE_JSON", fake)
    rc = mi.cmd_register("tavily", "tvly-x", host=None, dry_run=False)
    assert rc == 3
    assert "解析失败" in capsys.readouterr().err


def test_unregister_returns_3_on_corrupt_claude_json(tmp_path, monkeypatch):
    fake = tmp_path / ".claude.json"
    fake.write_text("garbage{", encoding="utf-8")
    monkeypatch.setattr(mi, "CLAUDE_JSON", fake)
    assert mi.cmd_unregister("tavily") == 3


# ════════════════════════════════════════════════════════
# 9. write_claude_json: chmod 0600 实际生效（POSIX 平台）
# ════════════════════════════════════════════════════════

def test_write_claude_json_chmod_0600(tmp_path, monkeypatch):
    if sys.platform == "win32":
        pytest.skip("Windows NTFS 不支持 POSIX chmod 语义")
    fake = tmp_path / ".claude.json"
    monkeypatch.setattr(mi, "CLAUDE_JSON", fake)
    mi.write_claude_json({"mcpServers": {"tavily": {"env": {"TAVILY_API_KEY": "sensitive"}}}})
    import stat
    mode = stat.S_IMODE(fake.stat().st_mode)
    assert mode == 0o600, f"expected 0o600 got {oct(mode)}"


def test_write_claude_json_chmod_failure_warns_does_not_raise(tmp_path, monkeypatch, capsys):
    """chmod 失败（如 Win NTFS / SMB FS）应只 stderr WARN，不让 register 整体失败。

    rationale: tw_config.py 同款设计（line 121-128）— Win 用户 register 不能因
    chmod 失败而 fail，否则跨平台不可用。
    """
    fake = tmp_path / ".claude.json"
    monkeypatch.setattr(mi, "CLAUDE_JSON", fake)

    def fake_chmod(path, mode, **kwargs):
        # 接受 follow_symlinks 等 kwarg（shutil.copystat 内部调用会传）
        raise OSError(13, "Permission denied (mocked)")
    monkeypatch.setattr(mi.os, "chmod", fake_chmod)

    # write 不应 raise
    mi.write_claude_json({"mcpServers": {}})
    err = capsys.readouterr().err
    assert "WARN" in err
    assert "chmod 0600 failed" in err

    # 进一步验证：cmd_register 在 chmod 失败时仍 return 0（用户级 happy path 仍走通）
    capsys.readouterr()  # 清空
    rc = mi.cmd_register("tavily", "tvly-x", host=None, dry_run=False)
    assert rc == 0
    err2 = capsys.readouterr().err
    assert "WARN" in err2  # 用户能从 stderr 看到权限问题


# ════════════════════════════════════════════════════════
# 10. cmd_test: control flow（mock Popen + send/recv_jsonrpc）
# ════════════════════════════════════════════════════════

class _FakePopenForTest:
    """模拟 subprocess.Popen 但不真起进程。

    reader thread 会调 iter(stdout.readline, "")；用空 stdout 让 thread 立即 EOF 退出。
    cmd_test 真正的 control flow 通过 monkeypatch send_jsonrpc / recv_jsonrpc 验证。
    """
    def __init__(self, *args, **kwargs):
        import io
        self.stdin = io.StringIO()
        self.stdout = io.StringIO()  # readline() → ""，reader thread 立即退出
        self.stderr = io.StringIO()
    def terminate(self): pass
    def wait(self, timeout=None): pass
    def kill(self): pass


@pytest.fixture
def mocked_test_proc(monkeypatch):
    """让 cmd_test 不真起 server；recv_jsonrpc 由测试逐项 push response。"""
    monkeypatch.setattr(mi.subprocess, "Popen", _FakePopenForTest)
    sent: list[dict] = []
    monkeypatch.setattr(mi, "send_jsonrpc", lambda proc, msg: sent.append(msg))
    return sent


def test_cmd_test_unknown_provider(capsys):
    assert mi.cmd_test("doesnotexist", key="k", host=None) == 2


def test_cmd_test_no_key_fails(tmp_path, monkeypatch, capsys):
    fake = tmp_path / ".claude.json"
    monkeypatch.setattr(mi, "CLAUDE_JSON", fake)  # 不存在 → no key from json
    assert mi.cmd_test("tavily", key=None, host=None) == 1
    assert "no key" in capsys.readouterr().err


def test_cmd_test_invalid_minimax_key_returns_2(tmp_path, monkeypatch):
    fake = tmp_path / ".claude.json"
    monkeypatch.setattr(mi, "CLAUDE_JSON", fake)
    assert mi.cmd_test("minimax", key="wrong-prefix", host=None) == 2


def test_cmd_test_minimax_full_pass(mocked_test_proc, monkeypatch, capsys):
    """minimax test 跑 initialize + 2 tool/call 全 PASS → 返回 0"""
    sent = mocked_test_proc
    responses = iter([
        {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}},  # initialize
        {"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "search ok"}]}},
        {"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": "image ok"}]}},
    ])
    monkeypatch.setattr(mi, "recv_jsonrpc", lambda q, expected_id, timeout: next(responses))
    rc = mi.cmd_test("minimax", key="sk-cp-test", host=None)
    assert rc == 0
    out = capsys.readouterr().out
    assert "PASS web_search" in out
    assert "PASS understand_image" in out
    # 验证发送顺序：initialize → notif → 2 tool/call
    methods = [m.get("method") for m in sent]
    assert methods == ["initialize", "notifications/initialized", "tools/call", "tools/call"]


def test_cmd_test_minimax_partial_fail_continues(mocked_test_proc, monkeypatch, capsys):
    """web_search PASS 但 understand_image isError → 仍跑两个 tool，最终返回 1"""
    responses = iter([
        {"jsonrpc": "2.0", "id": 1, "result": {}},
        {"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "ok"}]}},
        {"jsonrpc": "2.0", "id": 3, "result": {"isError": True,
                                                "content": [{"type": "text", "text": "image too large"}]}},
    ])
    monkeypatch.setattr(mi, "recv_jsonrpc", lambda q, expected_id, timeout: next(responses))
    rc = mi.cmd_test("minimax", key="sk-cp-test", host=None)
    assert rc == 1
    out = capsys.readouterr().out
    assert "PASS web_search" in out
    assert "FAIL understand_image" in out
    assert "image too large" in out


def test_cmd_test_initialize_error_returns_1(mocked_test_proc, monkeypatch, capsys):
    """initialize 阶段 server 报错 → 不再继续 tool/call，立即返回 1"""
    responses = iter([
        {"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "bad request"}},
    ])
    monkeypatch.setattr(mi, "recv_jsonrpc", lambda q, expected_id, timeout: next(responses))
    rc = mi.cmd_test("tavily", key="tvly-x", host=None)
    assert rc == 1
    assert "initialize" in capsys.readouterr().out
