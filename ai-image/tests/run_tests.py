"""Simple ai-image plugin test runner (no pytest dependency).

Discovers all test_*.py in this directory and runs them as separate processes.
Mirrors the solution-master/tests/run_unit_tests.py self-rolled style.
"""

import os
import subprocess
import sys


def main() -> int:
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    test_files = sorted(
        f for f in os.listdir(tests_dir)
        if f.startswith("test_") and f.endswith(".py")
    )
    if not test_files:
        print("no test_*.py files found", file=sys.stderr)
        return 1

    failed = 0
    for f in test_files:
        print(f"\n=== {f} ===")
        rc = subprocess.call([sys.executable, os.path.join(tests_dir, f)])
        if rc != 0:
            failed += 1

    print(f"\n{'='*40}")
    if failed:
        print(f"FAILED: {failed}/{len(test_files)} test files")
        return 1
    print(f"PASSED: {len(test_files)}/{len(test_files)} test files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
