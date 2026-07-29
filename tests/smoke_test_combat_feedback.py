"""
Optional smoke test for Avrae combat feedback without Discord.

Run:
    python tests/smoke_test_combat_feedback.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    channel_id = "combat-test-channel"
    runtime.combat_feedback_service.register_encounter(
        channel_id=channel_id,
        room_id="room_1",
        monsters=[{"name": "Goblin", "count": 2}],
        xp_reward_total=100,
    )

    print(runtime.combat_feedback_service.process_text(channel_id, "Goblin is dead"))
    print(runtime.combat_feedback_service.process_text(channel_id, "Goblin defeated"))
    print(runtime.combat_repo.get_combat_state(channel_id))


if __name__ == "__main__":
    main()
