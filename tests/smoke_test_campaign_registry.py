
"""
Optional smoke test for campaign registry and active campaign selection.
Run:
    python tests/smoke_test_campaign_registry.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    channel_id = "campaign-test-channel"
    runtime.campaign_service.ensure_campaign("MoG_TEST", name="Moon over Graymoor Test")
    print(runtime.campaign_service.set_active_campaign(channel_id, "MoG_TEST"))
    print(runtime.campaign_service.status_text(channel_id))
    print(runtime.campaign_service.list_campaigns_text())
    context = runtime.context_service.get_context(channel_id, "player-1", "Who is George Gilly?")
    print(context.get("campaign_id"))


if __name__ == "__main__":
    main()
