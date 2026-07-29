"""
Optional smoke test for deterministic movement/navigation.
Run:
    python tests/smoke_test_navigation.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    channel_id = "nav-test-channel"
    player_id = "player-1"

    runtime.location_repo.upsert_room({
        "room_id": "room_1",
        "title": "Bejárat",
        "facts": "Egy hideg, nyirkos bejárati csarnok.",
        "exits": {"north": "room_2"},
    })
    runtime.location_repo.upsert_room({
        "room_id": "room_2",
        "title": "Őrszoba",
        "facts": "Régi fegyverállványok sorakoznak a fal mellett.",
        "exits": {"south": "room_1"},
    })
    runtime.channel_repo.set_location(channel_id, "room_1")

    output = runtime.game_turn_service.process(channel_id, player_id, "Megyünk észak felé.")
    print(output)
    print(runtime.channel_repo.get_state(channel_id))


if __name__ == "__main__":
    main()
