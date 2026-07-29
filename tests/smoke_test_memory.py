"""
Optional smoke test for persistent memory event logging.
Run:
    python tests/smoke_test_memory.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    channel_id = "memory-test-channel"
    player_id = "player-1"

    runtime.location_repo.upsert_room({
        "room_id": "memory_room_1",
        "title": "Emlékcsarnok",
        "facts": "Hideg kőfalak és halvány fény.",
        "exits": {"north": "memory_room_2"},
    })
    runtime.location_repo.upsert_room({
        "room_id": "memory_room_2",
        "title": "Második terem",
        "facts": "Poros terem.",
        "exits": {"south": "memory_room_1"},
    })
    runtime.channel_repo.set_location(channel_id, "memory_room_1")

    print(runtime.game_turn_service.process(channel_id, player_id, "Megyünk észak felé."))
    events = runtime.memory_repo.list_recent_events(channel_id, limit=10)
    print(events)
    print(runtime.memory_summary_service.build_recent_summary(events))


if __name__ == "__main__":
    main()
