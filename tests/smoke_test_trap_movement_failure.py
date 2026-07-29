"""
Optional smoke test for trap on failed movement.
Run:
    python tests/smoke_test_trap_movement_failure.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    channel_id = "trap-test-channel"
    player_id = "player-1"

    runtime.location_repo.upsert_room({
        "room_id": "room_1",
        "title": "Csapdás előtér",
        "facts": "A terem nyugati fala előtt rejtett trap található. DC 13, 1d6 piercing damage.",
        "exits": {"north": "room_2"},
        "traps": [
            {
                "name": "hidden_wall_spikes",
                "trigger_on": ["exit_not_found", "exit_failure"],
                "damage": 4,
                "damage_type": "piercing",
                "required_check": "Dexterity Save",
                "dc": 13,
                "effect_tags": ["damage"],
                "once": True,
                "description": "A falból rozsdás tüskék csapódnak elő."
            }
        ]
    })
    runtime.location_repo.upsert_room({"room_id": "room_2", "title": "Folyosó", "facts": "Keskeny folyosó.", "exits": {"south": "room_1"}})
    runtime.channel_repo.set_location(channel_id, "room_1")

    output = runtime.game_turn_service.process(channel_id, player_id, "Megyünk nyugat felé.")
    print(output)
    print(runtime.channel_repo.get_state(channel_id).get("trap_state"))


if __name__ == "__main__":
    main()
