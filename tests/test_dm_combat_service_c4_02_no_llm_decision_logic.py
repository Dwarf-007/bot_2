from pathlib import Path


def test_dm_combat_service_uses_monster_decision_service_import():
    text = Path("services/dm_combat_service.py").read_text(encoding="utf-8")

    assert "from services.monster_decision_service import MonsterDecisionService" in text
    assert "self.decision_service = decision_service or MonsterDecisionService" in text


def test_dm_combat_service_no_longer_builds_monster_decision_prompt_inline():
    text = Path("services/dm_combat_service.py").read_text(encoding="utf-8")

    assert "Lehetséges akciók:" not in text
    assert "Válassz egy akciót" not in text
    assert "json.loads(response)" not in text


def test_monster_decision_service_has_no_io_or_dispatch_markers():
    text = Path("services/monster_decision_service.py").read_text(encoding="utf-8")

    assert "dispatch_commands" not in text
    assert "AvraeDispatcher" not in text
    assert "AvraeClient" not in text
    assert "message.channel.send" not in text
    assert "TurnOutput" not in text
