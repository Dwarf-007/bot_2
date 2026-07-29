"""
Optional smoke test for the refactored game turn pipeline.
Run manually from project root after applying refactor packages:

    python tests/smoke_test_game_turn.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


class FakeLLM:
    def generate(self, prompt: str) -> str:
        return """
        {
          "narrative": "A folyosó végén hideg huzat mozdul.",
          "required_check": "Perception",
          "dc": 12,
          "next_room_id": null,
          "xp_reward": 0,
          "milestone_reached": false,
          "inventory_update": {"gold": 0.0, "items": {}, "ammo": {}},
          "avrae_sync_damage": null,
          "secret_messages": [],
          "rest_consequence": {"rest_type": "NONE", "status": "NONE", "ambush_monster": null},
          "confidence": "high",
          "source_usage": "source_based",
          "needs_clarification": false,
          "dm_notes": []
        }
        """


def main() -> None:
    runtime = build_runtime()
    runtime.game_turn_service.llm_adapter = FakeLLM()
    output = runtime.game_turn_service.process("test-channel", "test-player", "Megvizsgálom a folyosót.")
    print(output)


if __name__ == "__main__":
    main()
