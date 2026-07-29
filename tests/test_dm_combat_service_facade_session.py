from types import SimpleNamespace

from services.dm_combat_service import DMCombatService


class FakeLLM:
    def generate(self, prompt):
        return '{"action_index": 0, "target_id": "p1", "reason": "test"}'


class FakeBestiary:
    def get_monster_stats(self, name):
        return {
            "hp": {"average": 7},
            "ac": [13],
            "attack_bonus": 4,
            "damage": "1d6+2",
            "xp": 50,
            "action": [
                {"name": "Scimitar", "type": "melee", "attack_bonus": 4, "damage": "1d6+2"}
            ],
        }


def test_dm_combat_service_start_combat_is_facade_over_session_service():
    service = DMCombatService(llm_adapter=FakeLLM(), bestiary_service=FakeBestiary())

    output = service.start_combat("c1", [{"name": "Goblin", "count": 1}])

    assert service.is_active("c1") is True
    assert service.get_combat_state("c1") is service.session_service.get_combat_state("c1")
    assert service._combats is service.session_service.combats
    assert output.avrae_commands == []
    assert output.suggested_commands == ["!init begin", "!init add 1 Goblin -hp 7"]
    assert output.dm_instructions


def test_dm_combat_service_roll_feedback_delegates_to_session_service():
    service = DMCombatService(llm_adapter=FakeLLM(), bestiary_service=FakeBestiary())
    service.start_combat("c1", [{"name": "Goblin", "count": 1}])

    event = SimpleNamespace(payload={"channel_id": "c1", "actor": "Alice", "formula": "1d20+5", "total": 17})
    service.on_player_roll(event)

    assert service.get_combat_state("c1").player_rolls == [
        {"actor": "Alice", "formula": "1d20+5", "total": 17}
    ]


def test_dm_combat_service_execute_monster_turn_still_returns_advisory_output():
    service = DMCombatService(llm_adapter=FakeLLM(), bestiary_service=FakeBestiary())
    service.start_combat("c1", [{"name": "Goblin", "count": 1}])
    service.set_player_ac("c1", "p1", 12)

    output = service.execute_monster_turn("c1")

    assert output is not None
    assert output.public_narrative
    assert output.suggested_commands
    assert output.suggested_commands[0].startswith("!r 1d20+")
    assert output.avrae_commands == []
