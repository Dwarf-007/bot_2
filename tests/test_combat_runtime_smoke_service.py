from services.combat_runtime_smoke_service import CombatRuntimeSmokeService


def test_combat_runtime_smoke_service_green_path():
    result = CombatRuntimeSmokeService().run(channel_id="c1")

    assert result.ok is True, result.summary_text()
    assert result.active_after_start is True
    assert result.no_legacy_avrae_commands is True
    assert any("Harc kezdődik" in narrative for narrative in result.public_narratives)
    assert any("Goblin 1 megtámadja" in narrative for narrative in result.public_narratives)
    assert "!init begin" in result.suggested_commands
    assert any(command.startswith("!r 1d20+") for command in result.suggested_commands)
    assert any("Monster decision source" in note for note in result.debug_notes)


def test_combat_runtime_smoke_result_has_machine_readable_dict_and_summary():
    result = CombatRuntimeSmokeService().run(channel_id="c1")

    data = result.to_dict()
    assert data["ok"] is True
    assert data["steps"]
    assert data["suggested_commands"]
    assert "Combat Runtime smoke:" in result.summary_text()


def test_combat_runtime_smoke_steps_are_explicit():
    result = CombatRuntimeSmokeService().run(channel_id="c1")
    names = [step.name for step in result.steps]

    assert "start_combat_public_narrative" in names
    assert "start_combat_suggested_commands" in names
    assert "start_combat_no_legacy_avrae_commands" in names
    assert "start_combat_state_active" in names
    assert "monster_turn_output_exists" in names
    assert "monster_turn_public_narrative" in names
    assert "monster_turn_suggested_roll_command" in names
    assert "monster_turn_no_legacy_avrae_commands" in names
    assert "monster_decision_debug_notes" in names
    assert "no_avrae_dispatcher_called" in names
