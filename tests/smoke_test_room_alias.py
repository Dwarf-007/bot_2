
"""
Optional smoke test for room alias lookup.
Run:
    python tests/smoke_test_room_alias.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    campaign_id = "ALIAS_TEST"
    channel_id = "alias-test-channel"
    runtime.campaign_service.ensure_campaign(campaign_id, name="Alias Test")
    runtime.campaign_service.set_active_campaign(channel_id, campaign_id)
    runtime.location_repo.upsert_room({
        "campaign_id": campaign_id,
        "room_id": "graymoor_bend_01",
        "title": "Graymoor Bend",
        "room_slug": "graymoor_bend",
        "facts": "A small town square.",
        "exits": {},
    })
    runtime.room_alias_service.ensure_room_aliases_from_room(campaign_id, {
        "room_id": "graymoor_bend_01",
        "title": "Graymoor Bend",
        "room_slug": "graymoor_bend",
    })
    print(runtime.admin_debug_service.find_room_text(channel_id, "Graymoor"))
    print(runtime.admin_debug_service.set_room(channel_id, "Graymoor Bend"))
    print(runtime.admin_debug_service.state_text(channel_id))


if __name__ == "__main__":
    main()
