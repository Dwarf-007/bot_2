"""
Optional smoke test for AdminDebugService without Discord.
Run:
    python tests/smoke_test_admin_debug.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    channel_id = "admin-test-channel"
    player_id = "player-1"

    runtime.location_repo.upsert_room({
        "room_id": "admin_room_1",
        "title": "Admin teszt szoba",
        "facts": "Teszt helyszín admin parancsokhoz.",
        "exits": {},
    })
    print(runtime.admin_debug_service.set_room(channel_id, "admin_room_1"))
    print(runtime.admin_debug_service.set_mode(channel_id, "campaign"))
    runtime.party_repo.add_player(channel_id, player_id)
    runtime.player_repo.add_xp(channel_id, player_id, 25)
    print(runtime.admin_debug_service.state_text(channel_id))
    print(runtime.admin_debug_service.party_text(channel_id))
    print(runtime.admin_debug_service.room_text("admin_room_1"))


if __name__ == "__main__":
    main()
