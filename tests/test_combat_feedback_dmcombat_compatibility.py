from types import SimpleNamespace

import pytest

from services.combat_feedback_service import CombatFeedbackService
from services.dm_combat_service import DMCombatService


class FakeLLM:
    def generate(self, prompt):
        return '{"action_index": 0, "target_id": "p1", "reason": "feedback compatibility"}'


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
        self.id = "c1"
        self.sent = []

    async def send(self, text):
        self.sent.append(text)


@pytest.mark.asyncio
async def test_combat_feedback_service_can_read_facade_compatibility_combats_and_render_advisory_output():
    dm_service = DMCombatService(
        llm_adapter=FakeLLM(),
        bestiary_service=FakeBestiary(),
        dice_service=DeterministicDice(),
    )
    dm_service.start_combat("c1", [{"name": "Goblin", "count": 1}])
    dm_service.set_player_ac("c1", "p1", 12)

    assert dm_service._combats is dm_service.session_service.combats
    assert "c1" in dm_service._combats

    feedback = CombatFeedbackService(
        combat_repo=FakeCombatRepo(),
        event_bus=FakeEventBus(),
        parser=FakeParser(),
        dm_combat_service=dm_service,
    )
    channel = FakeChannel()
    message = SimpleNamespace(channel=channel, content="Current turn: Goblin 1")

    await feedback._check_monster_turn(message)

    assert len(channel.sent) == 2
    assert "Goblin 1 megtámadja <@p1>-t" in channel.sent[0]
    assert "**DM instrukció**" in channel.sent[1]
    assert "**Javasolt DM / Avrae parancsok**" in channel.sent[1]
    assert "!r 1d20+4 # Goblin 1 attack" in channel.sent[1]
    assert "nem hajtja végre automatikusan" in channel.sent[1]
