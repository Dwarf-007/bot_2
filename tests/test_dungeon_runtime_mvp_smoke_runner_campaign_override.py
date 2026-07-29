from types import SimpleNamespace
from services.dungeon_runtime_mvp_smoke_runner import DungeonRuntimeMvpSmokeRunner
class Out:
    def __init__(self, t): self.public_narrative=t
class GTS:
    def __init__(self): self.campaigns=[]
    def process(self, ch,p,text,campaign_id_override=None):
        self.campaigns.append(campaign_id_override)
        return Out("ok")
    def bind_channel_campaign_for_smoke(self, **k): return True
class Resolver:
    def resolve(self,cid): return SimpleNamespace(visibility_available=True)
class Admin:
    def smoke_status(self, **k): return {"ok":True}
    def reset(self, **k): return {"ok":True}

def test_runner_forces_campaign_by_default():
    g=GTS()
    r=DungeonRuntimeMvpSmokeRunner(game_turn_service=g, resolver=Resolver(), state_admin_service=Admin())
    result=r.run(campaign_id="tenebrous", channel_id="ch", player_id="p")
    assert result.campaign_forced is True
    assert set(g.campaigns)=={"tenebrous"}

def test_runner_can_bind_channel():
    r=DungeonRuntimeMvpSmokeRunner(game_turn_service=GTS(), resolver=Resolver(), state_admin_service=Admin())
    result=r.run(campaign_id="tenebrous", channel_id="ch", player_id="p", bind_channel=True)
    assert result.channel_bound is True
