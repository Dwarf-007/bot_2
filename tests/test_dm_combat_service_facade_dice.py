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


class FakeDiceService:
    def __init__(self):
        self.attack_bonus_seen = None
        self.damage_str_seen = None

    def roll_d20_plus(self, bonus):
        self.attack_bonus_seen = bonus
        return 20

    def roll_damage(self, damage_str):
        self.damage_str_seen = damage_str
        return 4


def test_dm_combat_service_uses_injected_dice_service_for_monster_turn():
    dice = FakeDiceService()
    service = DMCombatService(
        llm_adapter=FakeLLM(),
        bestiary_service=FakeBestiary(),
        decision_service=FakeDecisionService(),
        dice_service=dice,
    )
    service.start_combat("c1", [{"name": "Goblin", "count": 1}])
    service.set_player_ac("c1", "p1", 12)

    output = service.execute_monster_turn("c1")

    assert dice.attack_bonus_seen == 6
    assert dice.damage_str_seen == "1d4"
    assert output is not None
    assert "4 sebzéssel" in output.public_narrative
    assert output.suggested_commands[0] == "!r 1d20+6 # Goblin 1 attack"
    assert output.avrae_commands == []


def test_dm_combat_service_roll_damage_wrapper_delegates_to_dice_service():
    dice = FakeDiceService()
    service = DMCombatService(
        llm_adapter=FakeLLM(),
        bestiary_service=FakeBestiary(),
        dice_service=dice,
    )

    assert service._roll_damage("2d8+1") == 4
    assert dice.damage_str_seen == "2d8+1"
