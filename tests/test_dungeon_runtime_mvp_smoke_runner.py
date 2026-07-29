from types import SimpleNamespace

from services.dungeon_runtime_mvp_smoke_runner import DungeonRuntimeMvpSmokeRunner


class FakeTurnOutput:
    def __init__(self, text):
        self.public_narrative = text


class FakeGameTurnService:
    def process(self, channel_id, player_id, text):
        low = text.casefold()
        if "titkos" in low:
            return FakeTurnOutput("secret ok")
        if "térkép" in low or "map" in low:
            return FakeTurnOutput("map ok")
        if "vissza" in low:
            return FakeTurnOutput("back ok")
        if "megyek" in low:
            return FakeTurnOutput("move ok")
        return FakeTurnOutput("look ok")


class FakeResolver:
    def __init__(self, bundle):
        self.bundle = bundle
    def resolve(self, campaign_id):
        return self.bundle


class FakeStateAdmin:
    def __init__(self):
        self.reset_called = False
    def smoke_status(self, *, campaign_id, channel_id):
        return {
            "ok": True,
            "campaign_id": campaign_id,
            "channel_id": channel_id,
            "visibility_available": True,
            "authoritative_exists": True,
        }
    def reset(self, **kwargs):
        self.reset_called = True
        return {"ok": True}


def test_runner_fails_when_bundle_missing():
    runner = DungeonRuntimeMvpSmokeRunner(
        game_turn_service=FakeGameTurnService(),
        resolver=FakeResolver(None),
        state_admin_service=FakeStateAdmin(),
    )
    result = runner.run(campaign_id="c1", channel_id="ch", player_id="p")
    assert result.ok is False
    assert result.bundle_available is False


def test_runner_fails_when_visibility_missing():
    bundle = SimpleNamespace(visibility_available=False)
    runner = DungeonRuntimeMvpSmokeRunner(
        game_turn_service=FakeGameTurnService(),
        resolver=FakeResolver(bundle),
        state_admin_service=FakeStateAdmin(),
    )
    result = runner.run(campaign_id="c1", channel_id="ch", player_id="p")
    assert result.ok is False
    assert result.bundle_available is True
    assert result.visibility_available is False


def test_runner_runs_smoke_against_available_bundle():
    admin = FakeStateAdmin()
    bundle = SimpleNamespace(visibility_available=True)
    runner = DungeonRuntimeMvpSmokeRunner(
        game_turn_service=FakeGameTurnService(),
        resolver=FakeResolver(bundle),
        state_admin_service=admin,
    )
    result = runner.run(campaign_id="c1", channel_id="ch", player_id="p", reset_before=True)
    assert result.ok is True
    assert result.bundle_available is True
    assert result.visibility_available is True
    assert admin.reset_called is True
    assert result.smoke_result is not None
    assert len(result.smoke_result.steps) == 6
