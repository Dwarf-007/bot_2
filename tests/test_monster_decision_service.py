from services.combat_session_service import CombatState, MonsterState
from services.monster_decision_service import MonsterDecisionService


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.response


def _state_and_monster():
    state = CombatState(channel_id="c1")
    state.player_ac = {"p1": 12, "p2": 14}
    monster = MonsterState(
        name="Goblin",
        unique_id="Goblin 1",
        max_hp=7,
        current_hp=7,
        ac=13,
        attack_bonus=4,
        damage_dice="1d6+2",
        xp=50,
        actions=[{"name": "Scimitar", "bonus": 4, "damage": "1d6+2"}],
    )
    return state, monster


def test_choose_action_uses_llm_json_decision():
    state, monster = _state_and_monster()
    llm = FakeLLM('{"action_index": 0, "target_id": "p2", "reason": "closest target"}')
    service = MonsterDecisionService(llm_adapter=llm)

    decision = service.choose_action(state, monster)

    assert decision.source == "llm"
    assert decision.action["name"] == "Scimitar"
    assert decision.target_id == "p2"
    assert decision.reason == "closest target"
    assert llm.prompts


def test_choose_action_falls_back_when_llm_response_is_invalid():
    state, monster = _state_and_monster()
    service = MonsterDecisionService(llm_adapter=FakeLLM("not json"))

    decision = service.choose_action(state, monster)

    assert decision.source == "fallback"
    assert decision.action["name"] == "basic attack"
    assert decision.target_id in {"p1", "p2"}
    assert decision.debug_notes == ["llm_decision_failed"]


def test_choose_action_without_llm_uses_basic_attack_fallback():
    state, monster = _state_and_monster()
    service = MonsterDecisionService()

    decision = service.choose_action(state, monster)

    assert decision.source == "fallback"
    assert decision.reason == "basic_attack_fallback"
    assert decision.action == {
        "type": "melee",
        "name": "basic attack",
        "bonus": 4,
        "damage": "1d6+2",
    }
    assert decision.target_id in {"p1", "p2"}
