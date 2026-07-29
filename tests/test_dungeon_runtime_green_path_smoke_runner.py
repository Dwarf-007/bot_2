from types import SimpleNamespace

from services.dungeon_runtime_green_path_smoke_runner import DungeonRuntimeGreenPathSmokeRunner


class Out:
    def __init__(self, text):
        self.public_narrative = text


class GTS:
    def __init__(self):
        self.calls = []
    def process(self, ch, p, text, campaign_id_override=None):
        self.calls.append((text, campaign_id_override))
        return Out("ok")
    def bind_channel_campaign_for_smoke(self, **kwargs):
        return True


class Resolver:
    def resolve(self, campaign_id):
        return SimpleNamespace(visibility_available=True)


class Admin:
    def smoke_status(self, **kwargs):
        return {"ok": True}
    def reset(self, **kwargs):
        return {"ok": True}


def test_green_path_runner_forces_campaign_and_binds_channel():
    gts = GTS()
    runner = DungeonRuntimeGreenPathSmokeRunner(game_turn_service=gts, resolver=Resolver(), state_admin_service=Admin())
    result = runner.run(campaign_id="tenebrous", channel_id="ch", player_id="p", bind_channel=True)
    assert result.ok is True
    assert result.channel_bound is True
    assert {call[1] for call in gts.calls} == {"tenebrous"}
