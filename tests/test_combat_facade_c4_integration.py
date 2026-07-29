from services.dm_combat_service import DMCombatService


class FakeLLM:
    def generate(self, prompt):
        return '{"action_index": 0, "target_id": "p1", "reason": "integration test"}'


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


class DeterministicDice:
    def roll_d20_plus(self, bonus):
        return 20 + int(bonus or 0)

    def roll_damage(self, damage_str):
        return 6


def test_c4_facade_start_combat_and_monster_turn_green_path():
    service = DMCombatService(
        llm_adapter=FakeLLM(),
        bestiary_service=FakeBestiary(),
        dice_service=DeterministicDice(),
    )

    start = service.start_combat("c1", [{"name": "Goblin", "count": 1}])

    assert service.is_active("c1") is True
    assert service.get_combat_state("c1") is service.session_service.get_combat_state("c1")
    assert service._combats is service.session_service.combats
    assert "Harc kezdődik" in start.public_narrative
    assert start.avrae_commands == []
    assert start.suggested_commands == ["!init begin", "!init add 1 Goblin -hp 7"]
    assert start.dm_instructions

    service.set_player_ac("c1", "p1", 12)
    turn = service.execute_monster_turn("c1")

    assert turn is not None
    assert "Goblin 1 megtámadja <@p1>-t" in turn.public_narrative
    assert "6 sebzéssel" in turn.public_narrative
    assert turn.avrae_commands == []
    assert turn.suggested_commands[0] == "!r 1d20+4 # Goblin 1 attack"
    assert any("6 sebzést" in item for item in turn.suggested_commands)
    assert "Monster decision source: llm" in turn.debug_notes
    assert "Monster decision reason: integration test" in turn.debug_notes


def test_c4_facade_rejects_duplicate_active_combat():
    service = DMCombatService(llm_adapter=FakeLLM(), bestiary_service=FakeBestiary())

    first = service.start_combat("c1", [{"name": "Goblin", "count": 1}])
    second = service.start_combat("c1", [{"name": "Goblin", "count": 1}])

    assert "Harc kezdődik" in first.public_narrative
    assert second.public_narrative == "Már folyamatban van egy harc ezen a csatornán."
    assert second.suggested_commands == []
