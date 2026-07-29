from pathlib import Path


def test_dm_combat_service_uses_combat_recommendation_builder_import():
    text = Path("services/dm_combat_service.py").read_text(encoding="utf-8")

    assert "from services.combat_recommendation_builder import CombatRecommendationBuilder" in text
    assert "self.recommendation_builder = recommendation_builder or CombatRecommendationBuilder()" in text


def test_dm_combat_service_no_longer_builds_start_commands_inline():
    text = Path("services/dm_combat_service.py").read_text(encoding="utf-8")

    assert "suggested_commands = ["!init begin"]" not in text
    assert "!init add 1" not in text
    assert "Harc kezdődik!" not in text


def test_combat_recommendation_builder_has_no_io_or_dispatch_markers():
    text = Path("services/combat_recommendation_builder.py").read_text(encoding="utf-8")

    assert "dispatch_commands" not in text
    assert "AvraeDispatcher" not in text
    assert "AvraeClient" not in text
    assert "message.channel.send" not in text
    assert "llm_adapter" not in text
