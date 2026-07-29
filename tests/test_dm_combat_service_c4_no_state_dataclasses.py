from pathlib import Path


def test_dm_combat_service_no_longer_defines_state_dataclasses():
    text = Path("services/dm_combat_service.py").read_text(encoding="utf-8")

    assert "@dataclass
class MonsterState" not in text
    assert "@dataclass
class CombatState" not in text
    assert "from services.combat_session_service import CombatSessionService, CombatState, MonsterState" in text


def test_dm_combat_service_still_has_no_avrae_dispatch_markers():
    text = Path("services/dm_combat_service.py").read_text(encoding="utf-8")

    assert "dispatch_commands" not in text
    assert ".is_available()" not in text
    assert "AvraeClient" not in text
    assert "AvraeDispatcher" not in text
