from services.dm_combat_service import DMCombatService
from services.monster_decision_service import MonsterActionDecision


class FakeLLM:
    def generate(self, prompt):
        raise AssertionError("Injected decision_service should be used")


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


class FakeDecisionService:
    def choose_action(self, state, monster):
        return MonsterActionDecision(
            action={"name": "Scripted strike", "bonus": 6, "damage": "1d4"},
            target_id="p1",
            source="test",
            reason="scripted",
        )

    def choose_random_player(self, state):
        return "p1"


class FakeRecommendationBuilder:
    def __init__(self):
        self.start_called = False
        self.turn_called = False
        self.turn_input = None

    def build_start_combat_output(self, state):
        self.start_called = True
        from core.turn_output import TurnOutput
        return TurnOutput(public_narrative=f"start:{len(state.monsters)}")

    def build_monster_turn_output(self, data):
        self.turn_called = True
        self.turn_input = data
        from core.turn_output import TurnOutput
        return TurnOutput(public_narrative="turn", suggested_commands=[f"roll:{data.attack_bonus}"])

    def build_attack_narrative(self, monster, target_id, hit, damage):
        return "delegated"


def test_start_combat_delegates_output_to_recommendation_builder():
    builder = FakeRecommendationBuilder()
    service = DMCombatService(
        llm_adapter=FakeLLM(),
        bestiary_service=FakeBestiary(),
        decision_service=FakeDecisionService(),
        recommendation_builder=builder,
    )

    output = service.start_combat("c1", [{"name": "Goblin", "count": 1}])

    assert builder.start_called is True
    assert output.public_narrative == "start:1"


def test_execute_monster_turn_delegates_output_to_recommendation_builder():
    builder = FakeRecommendationBuilder()
    service = DMCombatService(
        llm_adapter=FakeLLM(),
        bestiary_service=FakeBestiary(),
        decision_service=FakeDecisionService(),
        recommendation_builder=builder,
    )
    service.start_combat("c1", [{"name": "Goblin", "count": 1}])
    service.set_player_ac("c1", "p1", 12)

    output = service.execute_monster_turn("c1")

    assert builder.turn_called is True
    assert builder.turn_input.monster.unique_id == "Goblin 1"
    assert builder.turn_input.target_id == "p1"
    assert builder.turn_input.attack_bonus == 6
    assert output.suggested_commands == ["roll:6"]
