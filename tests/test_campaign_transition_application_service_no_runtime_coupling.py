from pathlib import Path


def test_campaign_transition_application_service_has_no_avrae_or_discord_runtime_coupling():
    text = Path("services/campaign/campaign_transition_application_service.py").read_text(encoding="utf-8")

    assert "dispatch_commands" not in text
    assert "AvraeDispatcher" not in text
    assert "AvraeClient" not in text
    assert ".is_available()" not in text
    assert "message.channel.send" not in text
    assert "TurnOutput" not in text
