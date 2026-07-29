from pathlib import Path


def test_bot_core_router_is_not_wired_with_avrae_dispatcher():
    text = Path("bot/bot_core.py").read_text(encoding="utf-8")

    assert "DiscordTurnRouter(runtime.game_turn_service)" in text
    assert "DiscordTurnRouter(runtime.game_turn_service, avrae_dispatcher" not in text
    assert "getattr(runtime, 'avrae_dispatcher'" not in text
    assert 'getattr(runtime, "avrae_dispatcher"' not in text
