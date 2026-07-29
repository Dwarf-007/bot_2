from pathlib import Path


def test_bootstrap_does_not_import_or_create_canonical_avrae_dispatcher():
    text = Path("app/bootstrap.py").read_text(encoding="utf-8")

    assert "from services.avrae_client import AvraeClient" not in text
    assert "from services.avrae_dispatcher import AvraeDispatcher" not in text
    assert "AvraeClient(" not in text
    assert "AvraeDispatcher(" not in text
    assert "avrae_dispatcher: AvraeDispatcher" not in text
    assert "avrae_dispatcher=avrae_dispatcher" not in text


def test_bootstrap_keeps_combat_feedback_as_optional_inbound_adapter():
    text = Path("app/bootstrap.py").read_text(encoding="utf-8")

    assert "CombatFeedbackService" in text
    assert "AvraeParserService" in text
    assert "Optional inbound Avrae feedback" in text
