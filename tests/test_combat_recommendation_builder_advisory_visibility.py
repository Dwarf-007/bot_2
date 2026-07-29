from services.combat_recommendation_builder import CombatRecommendationBuilder, MonsterTurnAdvisoryInput
from services.combat_session_service import CombatState, MonsterState
from services.monster_decision_service import MonsterActionDecision


def _monster():
    return MonsterState(
        name="Goblin",
        unique_id="Goblin 1",
        max_hp=7,
        current_hp=7,
        ac=13,
        attack_bonus=4,
        damage_dice="1d6+2",
        xp=50,
    )


def test_start_combat_output_prints_dm_and_player_commands_in_public_narrative():
    state = CombatState(channel_id="c1", monsters={"Goblin 1": _monster()}, active=True)
    output = CombatRecommendationBuilder().build_start_combat_output(state)

    assert "**DM adja ki:**" in output.public_narrative
    assert "`!init begin`" in output.public_narrative
    assert "`!init add 1 Goblin -hp 7`" in output.public_narrative
    assert "**Játékosok adják ki:**" in output.public_narrative
    assert "`!init join`" in output.public_narrative
    assert "nem hajtja végre automatikusan" in output.public_narrative

    assert output.suggested_commands == [
        "!init begin",
        "!init add 1 Goblin -hp 7",
        "!init join",
    ]
    assert output.avrae_commands == []


def test_monster_turn_output_prints_suggested_roll_command_in_public_narrative():
    monster = _monster()
    decision = MonsterActionDecision(
        action={"name": "Scimitar", "bonus": 4, "damage": "1d6+2"},
        target_id="p1",
        source="test",
        reason="scripted",
    )
    data = MonsterTurnAdvisoryInput(
        monster=monster,
        target_id="p1",
        action=decision.action,
        attack_bonus=4,
        hit=True,
        damage=6,
        decision=decision,
    )

    output = CombatRecommendationBuilder().build_monster_turn_output(data)

    assert "Javasolt DM / Avrae parancsok" in output.public_narrative
    assert "`!r 1d20+4 # Goblin 1 attack`" in output.public_narrative
    assert "6 sebzést" in output.public_narrative
    assert "nem hajtja végre automatikusan" in output.public_narrative
    assert output.suggested_commands[0] == "!r 1d20+4 # Goblin 1 attack"
    assert output.avrae_commands == []
