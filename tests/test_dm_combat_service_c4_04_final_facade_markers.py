from pathlib import Path


def test_dm_combat_service_uses_combat_dice_service_import():
    text = Path("services/dm_combat_service.py").read_text(encoding="utf-8")

    assert "from services.combat_dice_service import CombatDiceService" in text
    assert "self.dice_service = dice_service or CombatDiceService()" in text


def test_dm_combat_service_no_longer_imports_random_or_regex_inline():
    text = Path("services/dm_combat_service.py").read_text(encoding="utf-8")

    assert "import random" not in text
    assert "import re" not in text
    assert "random.randint" not in text
    assert "re.match" not in text


def test_combat_dice_service_has_no_io_or_dispatch_markers():
    text = Path("services/combat_dice_service.py").read_text(encoding="utf-8")

    assert "dispatch_commands" not in text
    assert "AvraeDispatcher" not in text
    assert "AvraeClient" not in text
    assert "message.channel.send" not in text
    assert "llm_adapter" not in text
    assert "TurnOutput" not in text
