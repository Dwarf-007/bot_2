from services.dm_combat_service import DMCombatService


class FakeLLM:
    def generate(self, prompt):
        return '{"action_index": 0, "target_id": "p1", "reason": "visibility regression"}'


class FakeBestiary:
    def get_monster_stats(self, name):
        return {
            "hp": {"average": 7},
            "ac": [13],
            "attack_bonus": 4,
            "damage": "1d6+2",
            "xp": 50,
            "action": [{"name": "Scimitar", "attack_bonus": 4, "damage": "1d6+2"}],
        }


def test_dm_combat_service_start_combat_visibly_lists_dm_init_commands():
    service = DMCombatService(llm_adapter=FakeLLM(), bestiary_service=FakeBestiary())

    output = service.start_combat("c1", [{"name": "Goblin", "count": 1}])

    assert "`!init begin`" in output.public_narrative
    assert "`!init add 1 Goblin -hp 7`" in output.public_narrative
    assert "`!init join`" in output.public_narrative
    assert output.suggested_commands == ["!init begin", "!init add 1 Goblin -hp 7", "!init join"]
    assert output.avrae_commands == []
