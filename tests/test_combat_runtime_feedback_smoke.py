from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.game_events import EventTypes
from services.combat_feedback_service import CombatFeedbackService
from services.dm_combat_service import DMCombatService


class FakeLLM:
    def generate(self, prompt):
        return '{"action_index": 0, "target_id": "p1", "reason": "feedback smoke"}'


class FakeBestiary:
    def get_monster_stats(self, name):
        return {
            "hp": {"average": 7},
            "ac": [13],
            "attack_bonus": 4,
            "damage": "1d6+2",
            "xp": 50,
            "action": [
                {"name": "Scimitar", "type": "melee", "attack_bonus": 4, "damage": "1d6+2"}
            ],
        }


class DeterministicDice:
    def roll_d20_plus(self, bonus):
        return 20 + int(bonus or 0)

    def roll_damage(self, damage_str):
        return 5


class FakeCombatSnapshot:
    active = True
    room_id = "room-1"
    xp_reward_total = 50
    monsters = []


class FakeCombatRepo:
    def ensure_schema(self):
        pass

    def get_combat_state(self, channel_id):
        return FakeCombatSnapshot()

    def register_defeated_monster(self, channel_id, name):
        return False

    def clear_combat(self, channel_id):
        pass


class CapturingEventBus:
    def __init__(self):
        self.handlers = {}
        self.events = []

    def register(self, event_type, handler):
        self.handlers.setdefault(event_type, []).append(handler)

    def emit(self, event):
        self.events.append(event)
        for handler in self.handlers.get(event.type, []):
            handler(event)


class RollOnlyParser:
    def extract_full_text(self, message):
        return message.content

    def extract_current_turn_name(self, text):
        return ""

    def extract_roll_results(self, text):
        return [
            {"actor": "Alice", "formula": "1d20+5", "total": 17}
        ]

    def extract_defeated_names(self, text):
        return []


class CurrentTurnParser(RollOnlyParser):
    def extract_current_turn_name(self, text):
        return "Goblin 1" if "Goblin 1" in text else ""

    def extract_roll_results(self, text):
        return []


class FakeChannel:
    def __init__(self, channel_id="c1"):
        self.id = channel_id
        self.sent = []

    async def send(self, text):
        self.sent.append(text)


@pytest.mark.asyncio
async def test_feedback_smoke_player_roll_event_updates_dm_combat_session_rolls():
    dm_service = DMCombatService(
        llm_adapter=FakeLLM(),
        bestiary_service=FakeBestiary(),
        dice_service=DeterministicDice(),
    )
    dm_service.start_combat("c1", [{"name": "Goblin", "count": 1}])

    event_bus = CapturingEventBus()
    event_bus.register(EventTypes.PLAYER_ROLL, dm_service.on_player_roll)

    feedback = CombatFeedbackService(
        combat_repo=FakeCombatRepo(),
        event_bus=event_bus,
        parser=RollOnlyParser(),
        dm_combat_service=dm_service,
    )
    channel = FakeChannel("c1")
    message = SimpleNamespace(
        channel=channel,
        content="Alice rolls 1d20+5 = 17 for her attack.",
        embeds=[],
        author=SimpleNamespace(name="Avrae", display_name="Avrae"),
    )

    result = await feedback.process_avrae_message(message)

    assert len(result.roll_results) == 1
    assert result.roll_results[0]["actor"] == "Alice"
    assert result.roll_results[0]["formula"] == "1d20+5"
    assert result.roll_results[0]["total"] == 17

    assert len(event_bus.events) == 1
    assert event_bus.events[0].type == EventTypes.PLAYER_ROLL
    assert event_bus.events[0].payload["channel_id"] == "c1"

    state = dm_service.get_combat_state("c1")
    assert state.player_rolls == [
        {"actor": "Alice", "formula": "1d20+5", "total": 17}
    ]
    assert channel.sent == []


@pytest.mark.asyncio
async def test_feedback_smoke_current_monster_turn_renders_advisory_output_without_legacy_avrae_commands():
    dm_service = DMCombatService(
        llm_adapter=FakeLLM(),
        bestiary_service=FakeBestiary(),
        dice_service=DeterministicDice(),
    )
    dm_service.start_combat("c1", [{"name": "Goblin", "count": 1}])
    dm_service.set_player_ac("c1", "p1", 12)

    feedback = CombatFeedbackService(
        combat_repo=FakeCombatRepo(),
        event_bus=CapturingEventBus(),
        parser=CurrentTurnParser(),
        dm_combat_service=dm_service,
    )
    channel = FakeChannel("c1")
    message = SimpleNamespace(
        channel=channel,
        content="Current turn: Goblin 1",
        embeds=[],
        author=SimpleNamespace(name="Avrae", display_name="Avrae"),
    )

    await feedback.process_avrae_message(message)

    assert len(channel.sent) == 2
    assert "Goblin 1 megtámadja <@p1>-t" in channel.sent[0]
    assert "**DM instrukció**" in channel.sent[1]
    assert "**Javasolt DM / Avrae parancsok**" in channel.sent[1]
    assert "!r 1d20+4 # Goblin 1 attack" in channel.sent[1]
    assert "nem hajtja végre automatikusan" in channel.sent[1]


def test_feedback_smoke_service_has_no_outgoing_dispatch_markers():
    from pathlib import Path

    text = Path("services/combat_feedback_service.py").read_text(encoding="utf-8")

    assert "dispatch_commands" not in text
    assert "AvraeDispatcher" not in text
    assert "AvraeClient" not in text
    assert ".is_available()" not in text
