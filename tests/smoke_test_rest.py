"""
Optional smoke test for deterministic rest handling.
Run:
    python tests/smoke_test_rest.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    channel_id = "rest-test-channel"
    player_id = "player-1"

    runtime.location_repo.upsert_room({
        "room_id": "safe_room",
        "title": "Biztonságos kamra",
        "facts": "Csendes, zárható kis helyiség.",
        "exits": {},
    })
    runtime.channel_repo.set_location(channel_id, "safe_room")
    print(runtime.game_turn_service.process(channel_id, player_id, "Tartunk egy short restet."))

    runtime.location_repo.upsert_room({
        "room_id": "danger_room",
        "title": "Veszélyes barlang",
        "facts": "Veszélyes hely, wandering monster és ambush lehetőség.",
        "exits": {},
        "monsters": [{"name": "Goblin", "count": 1}],
    })
    runtime.channel_repo.set_location(channel_id, "danger_room")
    print(runtime.game_turn_service.process(channel_id, player_id, "Long restet tartunk."))
    print(runtime.combat_repo.get_combat_state(channel_id))


if __name__ == "__main__":
    main()
