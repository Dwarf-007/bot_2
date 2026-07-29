from core.game_events import EventTypes, GameEvent
from services.damage_event_handler import DamageEventHandler


def test_damage_event_handler_returns_suggested_damage_command():
    handler = DamageEventHandler()
    event = GameEvent(
        type=EventTypes.DAMAGE,
        payload={"amount": 5, "type": "piercing", "target": "@Player", "source": "trap"},
    )

    result = handler.handle(event)

    assert result["type"] == "suggested_command"
    assert result["system"] == "AVRAE"
    assert result["command"] == "!damage @Player 5[piercing]"
    assert result["reason"] == "trap"
    assert result["requires_dm_confirmation"] is True
    assert "manuálisan" in result["dm_instruction"]


def test_damage_event_handler_uses_player_placeholder_when_target_missing():
    handler = DamageEventHandler()
    event = GameEvent(type=EventTypes.DAMAGE, payload={"amount": "1d6", "type": "fire"})

    result = handler.handle(event)

    assert result["command"] == "!damage PLAYER 1d6[fire]"


def test_damage_event_handler_ignores_non_damage_events():
    handler = DamageEventHandler()
    event = GameEvent(type=EventTypes.COMBAT_START, payload={})

    assert handler.handle(event) is None
