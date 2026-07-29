from pathlib import Path


def test_combat_feedback_service_does_not_dispatch_avrae_commands():
    text = Path("services/combat_feedback_service.py").read_text(encoding="utf-8")

    assert "dispatch_commands" not in text
    assert "AvraeDispatcher" not in text
    assert "AvraeClient" not in text
    assert ".is_available()" not in text
