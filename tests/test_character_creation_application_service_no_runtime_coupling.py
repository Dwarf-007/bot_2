from pathlib import Path


def test_character_creation_application_service_has_no_avrae_or_discord_runtime_coupling():
    text = Path("services/compendium/character_creation_application_service.py").read_text(encoding="utf-8")

    assert "dispatch_commands" not in text
    assert "AvraeDispatcher" not in text
    assert "AvraeClient" not in text
    assert ".is_available()" not in text
    assert "message.channel.send" not in text


def test_character_creation_application_service_uses_turn_output_contract():
    text = Path("services/compendium/character_creation_application_service.py").read_text(encoding="utf-8")

    assert "from core.turn_output import TurnOutput" in text
    assert "suggested_commands=[]" in text
    assert "dm_instructions" in text
