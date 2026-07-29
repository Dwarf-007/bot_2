from services.game_turn_service import GameTurnService
class Repo:
    def __init__(self): self.saved=None
    def add_player(self,*a,**k): pass
    def append_context_message(self,*a,**k): pass
    def get_party_members(self,*a,**k): return []
    def get_state(self, channel_id): return {"campaign_id":"wrong","mode":"campaign"}
    def save_state(self, channel_id, state): self.saved=(channel_id,state)
class Dummy: pass
class Ctx: 
    def get_context(self, **k): return {}
class Prompt:
    def build(self,c,t): return t
class LLM:
    def generate(self,p): return "{}"
class Story:
    def apply(self, **k):
        from core.turn_output import TurnOutput
        return TurnOutput(public_narrative="story")
class Router:
    def try_handle_pre_llm(self, **k):
        from types import SimpleNamespace
        assert k["campaign_id"] == "tenebrous"
        return SimpleNamespace(handled=True, output={"handled":True,"ok":True,"text":"forced","raw":{}}, to_debug=lambda:{})

def test_process_uses_campaign_id_override():
    svc=GameTurnService(Repo(), Repo(), Ctx(), Prompt(), LLM(), Story(), runtime_mode_router=Router())
    out=svc.process("ch","p","look", campaign_id_override="tenebrous")
    assert out.public_narrative == "forced"

def test_bind_channel_campaign_for_smoke():
    repo=Repo()
    svc=GameTurnService(repo, repo, Ctx(), Prompt(), LLM(), Story())
    assert svc.bind_channel_campaign_for_smoke(channel_id="ch", campaign_id="tenebrous") is True
    assert repo.saved[1]["campaign_id"] == "tenebrous"
    assert repo.saved[1]["mode"] == "dungeon"
