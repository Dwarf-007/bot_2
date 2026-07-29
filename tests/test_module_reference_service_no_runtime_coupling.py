from pathlib import Path


def test_module_reference_service_has_no_avrae_or_discord_runtime_coupling():
    text = Path("services/compendium/module_reference_service.py").read_text(encoding="utf-8")

    assert "dispatch_commands" not in text
    assert "AvraeDispatcher" not in text
    assert "AvraeClient" not in text
    assert ".is_available()" not in text
    assert "message.channel.send" not in text
