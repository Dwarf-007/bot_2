from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from core.game_events import EventTypes
from services.combat_feedback_service import CombatFeedbackService


@dataclass
class FakeMonsterEntry:
    name: str
    remaining: int = 1


@dataclass
class FakeCombatSnapshot:
    channel_id: str
    active: bool
    room_id: str = "room-1"
    monsters: List[FakeMonsterEntry] = field(default_factory=list)
    xp_reward_total: int = 100


class FakeCombatRepo:
    def __init__(self):
        self.snapshot = FakeCombatSnapshot(
            channel_id="c1",
            active=True,
            monsters=[FakeMonsterEntry("Goblin", remaining=1)],
            xp_reward_total=100,
        )
        self.defeated_registered = []
        self.clear_calls = []

    def ensure_schema(self):
        pass

    def get_combat_state(self, channel_id):
        return self.snapshot

    def register_defeated_monster(self, channel_id, name):
        self.defeated_registered.append((channel_id, name))
        if name == "Goblin" and self.snapshot.active:
            self.snapshot.monsters = []
            self.snapshot.active = False
            return True
        return False

    def clear_combat(self, channel_id):
        self.clear_calls.append(channel_id)
        self.snapshot = FakeCombatSnapshot(
            channel_id=channel_id,
            active=False,
            monsters=[],
            xp_reward_total=0,
        )


class CapturingEventBus:
    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)


class DefeatedParser:
    def extract_defeated_names(self, text):
        return ["Goblin"] if "Goblin defeated" in text else []

    def extract_full_text(self, message):
        return message.content

    def extract_roll_results(self, text):
        return []

    def extract_current_turn_name(self, text):
        return ""


class NoDefeatParser(DefeatedParser):
    def extract_defeated_names(self, text):
        return []


def test_combat_end_smoke_emits_all_monsters_defeated_and_combat_end_events_and_clears_repo():
    repo = FakeCombatRepo()
    event_bus = CapturingEventBus()
    service = CombatFeedbackService(
        combat_repo=repo,
        event_bus=event_bus,
        parser=DefeatedParser(),
        dm_combat_service=None,
    )

    result = service.process_text("c1", "Goblin defeated")

    assert result.combat_ended is True
    assert result.all_monsters_defeated is True
    assert result.defeated_names == ["Goblin"]
    assert repo.defeated_registered == [("c1", "Goblin")]
    assert repo.clear_calls == ["c1"]

    event_types = [event.type for event in event_bus.events]
    assert EventTypes.ALL_MONSTERS_DEFEATED in event_types
    assert EventTypes.COMBAT_END in event_types

    all_defeated_event = next(event for event in event_bus.events if event.type == EventTypes.ALL_MONSTERS_DEFEATED)
    assert all_defeated_event.payload["channel_id"] == "c1"
    assert all_defeated_event.payload["room_id"] == "room-1"
    assert all_defeated_event.payload["xp_reward_total"] == 100
    assert all_defeated_event.payload["defeated_names"] == ["Goblin"]

    combat_end_event = next(event for event in event_bus.events if event.type == EventTypes.COMBAT_END)
    assert combat_end_event.payload == {"channel_id": "c1", "room_id": "room-1"}


def test_combat_end_smoke_no_defeat_does_not_emit_end_events_or_clear_repo():
    repo = FakeCombatRepo()
    event_bus = CapturingEventBus()
    service = CombatFeedbackService(
        combat_repo=repo,
        event_bus=event_bus,
        parser=NoDefeatParser(),
        dm_combat_service=None,
    )

    result = service.process_text("c1", "Nothing important happens")

    assert result.combat_ended is False
    assert result.all_monsters_defeated is False
    assert result.defeated_names == []
    assert repo.defeated_registered == []
    assert repo.clear_calls == []
    assert event_bus.events == []


def test_combat_end_smoke_unmatched_defeat_does_not_end_combat():
    repo = FakeCombatRepo()
    event_bus = CapturingEventBus()

    class UnmatchedDefeatedParser(DefeatedParser):
        def extract_defeated_names(self, text):
            return ["Orc"]

    service = CombatFeedbackService(
        combat_repo=repo,
        event_bus=event_bus,
        parser=UnmatchedDefeatedParser(),
        dm_combat_service=None,
    )

    result = service.process_text("c1", "Orc defeated")

    assert result.combat_ended is False
    assert result.all_monsters_defeated is False
    assert result.defeated_names == []
    assert repo.defeated_registered == [("c1", "Orc")]
    assert repo.clear_calls == []
    assert event_bus.events == []


def test_combat_end_smoke_service_has_no_outgoing_dispatch_markers():
    from pathlib import Path

    text = Path("services/combat_feedback_service.py").read_text(encoding="utf-8")

    assert "dispatch_commands" not in text
    assert "AvraeDispatcher" not in text
    assert "AvraeClient" not in text
    assert ".is_available()" not in text
