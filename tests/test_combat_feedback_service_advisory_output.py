from types import SimpleNamespace

import pytest

from core.turn_output import TurnOutput
from services.combat_feedback_service import CombatFeedbackService


class FakeCombatRepo:
    def ensure_schema(self):
        pass


class FakeEventBus:
    def emit(self, event):
        pass


class FakeParser:
    def extract_full_text(self, message):
        return message.content

    def extract_current_turn_name(self, text):
        return "Goblin 1" if "Goblin 1" in text else ""

    def extract_roll_results(self, text):
        return []

    def extract_defeated_names(self, text):
        return []


class FakeChannel:
    def __init__(self):
        self.sent = []

    async def send(self, text):
        self.sent.append(text)


class FakeDMCombatService:
    def __init__(self, output):
        self.output = output
        self._combats = {
            "c1": SimpleNamespace(
                monsters={
                    "Goblin 1": SimpleNamespace(unique_id="Goblin 1", name="Goblin")
                }
            )
        }

    def execute_monster_turn(self, channel_id):
        return self.output


@pytest.mark.asyncio
async def test_check_monster_turn_renders_suggested_commands_not_only_legacy_avrae_commands():
    output = TurnOutput(
        public_narrative="Goblin 1 támadásra lendül.",
        dm_instructions=["A DM döntse el, hogy kiadja-e a javasolt parancsot."],
        suggested_commands=["!r 1d20+4 # Goblin 1 attack"],
    )
    service = CombatFeedbackService(
        combat_repo=FakeCombatRepo(),
        event_bus=FakeEventBus(),
        parser=FakeParser(),
        dm_combat_service=FakeDMCombatService(output),
    )
    channel = FakeChannel()
    message = SimpleNamespace(channel=SimpleNamespace(id="c1", send=channel.send), content="Current turn: Goblin 1")

    await service._check_monster_turn(message)

    assert channel.sent[0] == "Goblin 1 támadásra lendül."
    assert "**DM instrukció**" in channel.sent[1]
    assert "!r 1d20+4 # Goblin 1 attack" in channel.sent[1]
    assert "nem hajtja végre automatikusan" in channel.sent[1]


def test_format_dm_guidance_merges_legacy_avrae_commands_for_compatibility():
    output = TurnOutput(
        suggested_commands=["!init begin"],
        avrae_commands=["!init begin", "!init add Goblin 1"],
    )

    text = CombatFeedbackService._format_dm_guidance(output)

    assert text.count("!init begin") == 1
    assert "!init add Goblin 1" in text
    assert "Javasolt DM / Avrae parancsok" in text
