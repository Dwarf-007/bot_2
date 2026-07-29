from pathlib import Path


def test_campaign_state_transition_proposal_service_has_no_runtime_coupling():
    text = Path("services/compendium/campaign_state_transition_proposal_service.py").read_text(encoding="utf-8")

    assert "dispatch_commands" not in text
    assert "AvraeDispatcher" not in text
    assert "AvraeClient" not in text
    assert ".is_available()" not in text
    assert "message.channel.send" not in text
    assert "TurnOutput" not in text
