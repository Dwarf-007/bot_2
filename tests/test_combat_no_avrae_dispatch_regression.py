from pathlib import Path


CANONICAL_FILES = [
    "app/bootstrap.py",
    "bot/bot_core.py",
    "bot/discord_router.py",
    "services/dm_combat_service.py",
    "services/combat_session_service.py",
    "services/monster_decision_service.py",
    "services/combat_recommendation_builder.py",
    "services/combat_dice_service.py",
    "services/combat_start_service.py",
    "services/combat_event_handler.py",
    "services/damage_event_handler.py",
    "services/combat_feedback_service.py",
    "services/encounter_service.py",
]


FORBIDDEN_DISPATCH_MARKERS = [
    "dispatch_commands",
    "AvraeDispatcher(",
    "AvraeClient(",
    ".is_available()",
]


def test_canonical_combat_path_has_no_avrae_auto_dispatch_markers():
    missing = []
    violations = []
    for file_name in CANONICAL_FILES:
        path = Path(file_name)
        if not path.exists():
            missing.append(file_name)
            continue
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_DISPATCH_MARKERS:
            if marker in text:
                violations.append((file_name, marker))

    assert missing == []
    assert violations == []


def test_event_handlers_no_longer_produce_legacy_avrae_command_type():
    for file_name in ["services/combat_event_handler.py", "services/damage_event_handler.py"]:
        text = Path(file_name).read_text(encoding="utf-8")
        assert '"type": "avrae_command"' not in text
        assert "'type': 'avrae_command'" not in text
        assert '"type": "suggested_command"' in text


def test_turn_output_legacy_avrae_commands_is_compatibility_only():
    text = Path("core/turn_output.py").read_text(encoding="utf-8")

    assert "suggested_commands" in text
    assert "dm_instructions" in text
    assert "all_suggested_commands" in text
    assert "must not be automatically dispatched" in text or "automatikusan" in text
