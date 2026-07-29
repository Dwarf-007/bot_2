from services.game_turn_service import GameTurnService


class DummyRepo:
    def __init__(self):
        self.state = {"campaign_id": "c1", "mode": "dungeon"}
    def add_player(self, *args, **kwargs):
        pass
    def append_context_message(self, *args, **kwargs):
        pass
    def get_party_members(self, *args, **kwargs):
        return []
    def get_state(self, channel_id):
        return self.state


class DummyContext:
    def get_context(self, **kwargs):
        return {}


class DummyPrompt:
    def build(self, context, text):
        return text


class DummyLLM:
    def generate(self, prompt):
        return "{}"


class DummyStory:
    def apply(self, **kwargs):
        from core.turn_output import TurnOutput
        return TurnOutput(public_narrative="story")


class DummyRouter:
    def try_handle_pre_llm(self, **kwargs):
        from types import SimpleNamespace
        return SimpleNamespace(
            handled=True,
            output={"handled": True, "ok": True, "text": "routed dungeon", "raw": {"ok": True}},
            to_debug=lambda: {"mode": "DUNGEON"},
        )


def test_game_turn_uses_runtime_mode_router_before_llm():
    svc = GameTurnService(
        channel_repo=DummyRepo(),
        party_repo=DummyRepo(),
        context_service=DummyContext(),
        prompt_builder=DummyPrompt(),
        llm_adapter=DummyLLM(),
        story_engine=DummyStory(),
        runtime_mode_router=DummyRouter(),
    )
    out = svc.process("ch", "p", "look")
    assert out.public_narrative == "routed dungeon"
