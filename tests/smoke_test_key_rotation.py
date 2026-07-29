"""
TOOLS/SMOKE_TEST_KEY_ROTATION.PY
Small local smoke test for GeminiKeyManager rotation behavior.

Run:
    python tools/smoke_test_key_rotation.py
"""

from __future__ import annotations

from llm.key_manager import GeminiKeyManager


def main() -> None:
    manager = GeminiKeyManager(["key-a", "key-b", "key-c"], cooldown_seconds=1)
    print(manager.next_key())  # key-a
    print(manager.next_key())  # key-b
    manager.report_failure("key-c", cooldown=1)
    print(manager.next_key())  # key-a or key-b, key-c skipped while cooling down
    print("available", manager.available_count())


if __name__ == "__main__":
    main()
