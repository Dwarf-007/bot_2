import pytest

from services.dm_combat_service import DMCombatService
from services.bestiary_service import BestiaryService
from core.turn_output import TurnOutput


class DummyLLM:
    def generate(self, prompt: str):
        return '{"action_index": 0, "target_id": "player1", "reason": "fallback"}'


class DummyDispatcher:
    def __init__(self):
        self.commands = []

    def is_available(self):
        return False

    def dispatch_commands(self, commands):
        self.commands.extend(commands)
        return {"status": "dispatched", "commands": commands}


def test_start_combat_generates_valid_init_commands():
    dm = DMCombatService(
        llm_adapter=DummyLLM(),
        bestiary_service=BestiaryService(path="data/bestiary.json"),
        avrae_dispatcher=DummyDispatcher(),
    )

    output = dm.start_combat(
        channel_id="test-channel",
        monsters_data=[{"name": "Stirge", "count": 2}],
        player_ids=["player1"],
    )

    assert isinstance(output, TurnOutput)
    assert any(cmd == "!init begin" for cmd in output.avrae_commands)
    assert any(cmd.startswith("!init add 1 Stirge") for cmd in output.avrae_commands)
    assert not any(cmd.startswith("!init add 0 ") for cmd in output.avrae_commands)
