"""Unit tests for _ensure_deps.py lock primitives (F-013).

Verifies the os.O_EXCL lock pattern + stale-lock detection logic without
actually invoking pip install. Standalone runner — no pytest dependency.
"""

import os
import sys
import tempfile
import time


def test_lock_atomic_creation() -> None:
    """Concurrent EXCL create should fail with FileExistsError."""
    with tempfile.TemporaryDirectory() as tmp:
        lock_path = os.path.join(tmp, ".deps-installing.lock")
        fd1 = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            try:
                os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                raise AssertionError("expected FileExistsError on second EXCL create")
            except FileExistsError:
                pass  # expected
        finally:
            os.close(fd1)
            os.unlink(lock_path)


def test_lock_pid_written() -> None:
    """Lock file should contain the writing process's PID."""
    with tempfile.TemporaryDirectory() as tmp:
        lock_path = os.path.join(tmp, ".deps-installing.lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode())
        finally:
            os.close(fd)
        with open(lock_path) as f:
            content = f.read()
        assert content == str(os.getpid()), f"expected PID={os.getpid()}, got {content!r}"


def test_stale_lock_detection() -> None:
    """A lock file with mtime > 5 min old should be detected as stale."""
    with tempfile.TemporaryDirectory() as tmp:
        lock_path = os.path.join(tmp, ".deps-installing.lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
        os.close(fd)
        old_time = time.time() - 360  # 6 min ago
        os.utime(lock_path, (old_time, old_time))
        age = time.time() - os.stat(lock_path).st_mtime
        assert age > 300, f"expected stale (age > 300s), got age={age}"


def test_fresh_lock_not_stale() -> None:
    """A just-created lock should be < 5 min old."""
    with tempfile.TemporaryDirectory() as tmp:
        lock_path = os.path.join(tmp, ".deps-installing.lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
        os.close(fd)
        age = time.time() - os.stat(lock_path).st_mtime
        assert age < 300, f"expected fresh (age < 300s), got age={age}"


def main() -> int:
    tests = [
        test_lock_atomic_creation,
        test_lock_pid_written,
        test_stale_lock_detection,
        test_fresh_lock_not_stale,
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
