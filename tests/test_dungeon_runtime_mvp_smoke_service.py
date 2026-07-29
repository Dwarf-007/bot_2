from services.dungeon_runtime_mvp_smoke_service import DungeonRuntimeMvpSmokeCommand, DungeonRuntimeMvpSmokeService


class FakeTurnOutput:
    def __init__(self, text):
        self.public_narrative = text


class FakeGameTurnService:
    def process(self, channel_id, player_id, text):
        low = text.casefold()
        if "titkos" in low or "secret" in low:
            return FakeTurnOutput("secret search ok")
        if "térkép" in low or "map" in low:
            return FakeTurnOutput("map ok")
        if "vissza" in low or "back" in low:
            return FakeTurnOutput("back ok")
        if "megyek" in low or "north" in low:
            return FakeTurnOutput("move ok")
        return FakeTurnOutput("look ok")


def test_mvp_smoke_service_runs_default_sequence():
    result = DungeonRuntimeMvpSmokeService(FakeGameTurnService()).run(channel_id="ch", player_id="p")
    assert result.ok is True
    assert len(result.steps) == 6
    assert "6/6 passed" in result.summary_text()


def test_mvp_smoke_service_reports_failed_expected_substring():
    commands = [DungeonRuntimeMvpSmokeCommand("bad", "look", expected_substring="missing")]
    result = DungeonRuntimeMvpSmokeService(FakeGameTurnService()).run(channel_id="ch", player_id="p", commands=commands)
    assert result.ok is False
    assert result.steps[0].ok is False
