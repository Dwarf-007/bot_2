from services.combat_recommendation_builder import CombatRecommendationBuilder, MonsterTurnAdvisoryInput
from services.combat_session_service import CombatState, MonsterState, MonsterTurnCompletion
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


def test_build_start_combat_output_contains_dm_instructions_and_suggested_commands():
    state = CombatState(channel_id="c1", monsters={"Goblin 1": _monster()}, active=True)
    builder = CombatRecommendationBuilder()

    output = builder.build_start_combat_output(state)

    assert "Harc kezdődik" in output.public_narrative
    assert output.avrae_commands == []
    assert output.suggested_commands == ["!init begin", "!init add 1 Goblin -hp 7"]
    assert output.dm_instructions


def test_build_monster_turn_output_contains_narrative_roll_and_debug_notes():
    monster = _monster()
    decision = MonsterActionDecision(
        action={"name": "Scimitar", "bonus": 4, "damage": "1d6+2"},
        target_id="p1",
        source="llm",
        reason="closest target",
    )
    data = MonsterTurnAdvisoryInput(
        monster=monster,
        target_id="p1",
        action=decision.action,
        attack_bonus=4,
        hit=True,
        damage=6,
        decision=decision,
        completion=MonsterTurnCompletion(),
    )
    builder = CombatRecommendationBuilder()

    output = builder.build_monster_turn_output(data)

    assert "Goblin 1 megtámadja <@p1>-t" in output.public_narrative
    assert "**találat** 6" in output.public_narrative
    assert output.suggested_commands[0] == "!r 1d20+4 # Goblin 1 attack"
    assert "6 sebzést" in output.suggested_commands[1]
    assert "Monster decision source: llm" in output.debug_notes
    assert "Monster decision reason: closest target" in output.debug_notes


def test_build_monster_turn_output_appends_combat_end_summary():
    monster = _monster()
    decision = MonsterActionDecision(action={}, target_id=None, source="fallback")
    data = MonsterTurnAdvisoryInput(
        monster=monster,
        target_id=None,
        action={},
        attack_bonus=4,
        hit=False,
        damage=0,
        decision=decision,
        completion=MonsterTurnCompletion(
            removed_monster_id="Goblin 1",
            all_monsters_defeated=True,
            total_xp=50,
        ),
    )

    output = CombatRecommendationBuilder().build_monster_turn_output(data)

    assert "💀 Goblin 1 elpusztult!" in output.public_narrative
    assert "Minden szörny legyőzve" in output.public_narrative
    assert "Szerezett XP: 50" in output.public_narrative
