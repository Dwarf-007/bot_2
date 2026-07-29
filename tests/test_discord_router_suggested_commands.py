import pytest

from bot.discord_router import DiscordTurnRouter
from core.turn_output import TurnOutput


class DummyChannel:
    def __init__(self):
        self.sent = []

    async def send(self, text):
        self.sent.append(text)


class DummyMessage:
    def __init__(self):
        self.channel = DummyChannel()
        self.guild = None
        self.client = None


class FailingDispatcher:
    def __init__(self):
        self.called = False

    def is_available(self):
        self.called = True
        return True

    def dispatch_commands(self, commands):
        self.called = True
        raise AssertionError("C3.2 router must not dispatch Avrae commands")


def test_format_dm_guidance_includes_instructions_and_suggested_commands():
    output = TurnOutput(
        dm_instructions=["Indítsd el a harcot Avrae-ban, ha a party felveszi a harcot."],
        suggested_commands=["!init begin", "!init add Skeleton 1"],
    )

    text = DiscordTurnRouter._format_dm_guidance(output)

    assert "**DM instrukció**" in text
    assert "Indítsd el a harcot" in text
    assert "**Javasolt DM / Avrae parancsok**" in text
    assert "!init begin" in text
    assert "!init add Skeleton 1" in text
    assert "nem hajtja végre automatikusan" in text


def test_format_dm_guidance_merges_legacy_avrae_commands():
    output = TurnOutput(
        suggested_commands=["!init begin"],
        avrae_commands=["!init begin", "!init add Goblin 1"],
    )

    text = DiscordTurnRouter._format_dm_guidance(output)

    assert text.count("!init begin") == 1
    assert "!init add Goblin 1" in text


@pytest.mark.asyncio
async def test_send_turn_output_does_not_call_avrae_dispatcher():
    dispatcher = FailingDispatcher()
    router = DiscordTurnRouter(game_turn_service=None, avrae_dispatcher=dispatcher)
    message = DummyMessage()
    output = TurnOutput(
        public_narrative="A csontvázak előlépnek.",
        suggested_commands=["!init begin", "!init add Skeleton 1"],
    )

    await router.send_turn_output(message, output)

    assert dispatcher.called is False
    assert message.channel.sent[0] == "A csontvázak előlépnek."
    assert "!init begin" in message.channel.sent[1]
    assert "!init add Skeleton 1" in message.channel.sent[1]
