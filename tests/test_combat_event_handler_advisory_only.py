from core.game_events import EventTypes, GameEvent
from services.combat_event_handler import CombatEventHandler


def test_combat_event_handler_returns_suggested_commands_not_avrae_commands():
    handler = CombatEventHandler()
    event = GameEvent(
        type=EventTypes.COMBAT_START,
        payload={
            "source": "test",
            "monsters": [
                {"name": "Goblin", "count": 2},
                {"monster_name": "Skeleton", "count": "1"},
            ],
        },
    )

    commands = handler.handle(event)

    assert commands == [
        {
            "type": "suggested_command",
            "system": "AVRAE",
            "command": "!init begin",
            "reason": "test",
            "requires_dm_confirmation": True,
        },
        {
            "type": "suggested_command",
            "system": "AVRAE",
            "command": "!init add Goblin 2",
            "reason": "combat_start_monster_add",
            "requires_dm_confirmation": True,
        },
        {
            "type": "suggested_command",
            "system": "AVRAE",
            "command": "!init add Skeleton 1",
            "reason": "combat_start_monster_add",
            "requires_dm_confirmation": True,
        },
    ]
    assert all(item["type"] != "avrae_command" for item in commands)


def test_combat_event_handler_ignores_non_combat_start_events():
    handler = CombatEventHandler()
    event = GameEvent(type=EventTypes.DAMAGE, payload={"amount": 5})

    assert handler.handle(event) is None
