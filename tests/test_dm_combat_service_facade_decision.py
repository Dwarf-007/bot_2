from services.dm_combat_service import DMCombatService
from services.monster_decision_service import MonsterActionDecision


class FakeLLM:
    def generate(self, prompt):
        raise AssertionError("Injected decision_service should be used instead of llm_adapter")


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


class FakeDecisionService:
    def __init__(self):
        self.called = False

    def choose_action(self, state, monster):
        self.called = True
        return MonsterActionDecision(
            action={"name": "Scripted strike", "bonus": 6, "damage": "1d4"},
            target_id="p1",
            source="test",
            reason="scripted",
        )

    def choose_random_player(self, state):
        return "p1"


def test_dm_combat_service_delegates_monster_decision_to_decision_service():
    decision_service = FakeDecisionService()
    service = DMCombatService(
        llm_adapter=FakeLLM(),
        bestiary_service=FakeBestiary(),
        decision_service=decision_service,
    )
    service.start_combat("c1", [{"name": "Goblin", "count": 1}])
    service.set_player_ac("c1", "p1", 12)

    output = service.execute_monster_turn("c1")

    assert decision_service.called is True
    assert output is not None
    assert output.suggested_commands[0] == "!r 1d20+6 # Goblin 1 attack"
    assert "Monster decision source: test" in output.debug_notes
    assert "Monster decision reason: scripted" in output.debug_notes
    assert output.avrae_commands == []
