"""Unit tests for backend_common.sanitize_error (F-012).

Verifies that common API key shapes are masked from exception strings before logging.
Standalone runner — no pytest dependency (matches solution-master/tests/run_unit_tests.py
self-rolled style).
"""

import os
import sys

# 兼容 plugin install 模式（PATH 注入）+ 本地开发（相对路径）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "gen", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "gen", "scripts", "image_backends"))
from backend_common import sanitize_error  # noqa: E402


def test_bearer_token() -> None:
    masked = sanitize_error("Bearer sk-or-1234567890abcdef1234")
    assert "***" in masked, f"expected mask in: {masked}"
    assert "sk-or-1234567890abcdef1234" not in masked, f"key leaked: {masked}"


def test_authorization_header() -> None:
    masked = sanitize_error("Authorization: Bearer abcdef1234567890abcdef")
    assert "abcdef1234567890abcdef" not in masked, f"key leaked: {masked}"


def test_api_key_query_string() -> None:
    masked = sanitize_error("Request to https://api.test/v1?api_key=sk-1234567890abcdef failed")
    assert "sk-1234567890abcdef" not in masked, f"key leaked: {masked}"


def test_token_query_string() -> None:
    masked = sanitize_error("https://api.test/v1?token=mysecrettoken123456789")
    assert "mysecrettoken123456789" not in masked


def test_x_api_key_header() -> None:
    masked = sanitize_error("X-API-Key: sk-abcdef1234567890abcdef")
    assert "sk-abcdef1234567890abcdef" not in masked


def test_passthrough_safe_message() -> None:
    msg = "normal error without any key shape"
    assert sanitize_error(msg) == msg


def test_passthrough_short_string() -> None:
    # Short strings without key prefix patterns should pass through unchanged
    msg = "401 Unauthorized"
    assert sanitize_error(msg) == msg


def test_exception_object() -> None:
    # str() conversion should work on Exception objects
    exc = ValueError("API failed for sk-abcdef1234567890abcdef")
    masked = sanitize_error(exc)
    assert "sk-abcdef1234567890abcdef" not in masked


def main() -> int:
    tests = [
        test_bearer_token,
        test_authorization_header,
        test_api_key_query_string,
        test_token_query_string,
        test_x_api_key_header,
        test_passthrough_safe_message,
        test_passthrough_short_string,
        test_exception_object,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}", file=sys.stderr)
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
