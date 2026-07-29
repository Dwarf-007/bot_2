
"""
Optional smoke test for RuntimeHealthService.
Run:
    python tests/smoke_test_runtime_health.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    report = runtime.runtime_health_service.run_all(campaign_id="default", channel_id="health-test-channel")
    print(report.to_text())


if __name__ == "__main__":
    main()
