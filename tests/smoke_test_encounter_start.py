"""
Optional smoke test for encounter start integration.
Run:
    python tests/smoke_test_encounter_start.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime
from core.llm_response import CombatStartRequest, LLMResponse


def main() -> None:
    runtime = build_runtime()
    channel_id = "encounter-test-channel"
    player_id = "player-1"
    runtime.channel_repo.add_player(channel_id, player_id)

    response = LLMResponse(
        narrative="A sötétből két goblin ront elő.",
        combat_start=CombatStartRequest(
            enabled=True,
            monsters=[{"name": "Goblin", "count": 2}],
            xp_reward_total=100,
            encounter_type="STATIC_ROOM",
            difficulty="STANDARD",
        ),
    )
    output = runtime.story_engine.apply(channel_id, player_id, response, [player_id])
    print(output)
    print(runtime.combat_repo.get_combat_state(channel_id))


if __name__ == "__main__":
    main()
