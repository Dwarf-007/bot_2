from services.game_turn_service import GameTurnService


class DummyRepo:
    def add_player(self, *args, **kwargs):
        pass
    def append_context_message(self, *args, **kwargs):
        pass
    def get_party_members(self, *args, **kwargs):
        return []
    def get_state(self, channel_id):
        return {"campaign_id": "c1", "mode": "campaign"}


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


class DummyVisibilityAdapter:
    def try_handle(self, **kwargs):
        return {"handled": True, "ok": True, "text": "visibility handled", "raw": {"ok": True}}


def test_injected_visibility_adapter_is_used():
    svc = GameTurnService(
        channel_repo=DummyRepo(),
        party_repo=DummyRepo(),
        context_service=DummyContext(),
        prompt_builder=DummyPrompt(),
        llm_adapter=DummyLLM(),
        story_engine=DummyStory(),
        visibility_movement_adapter=DummyVisibilityAdapter(),
        runtime_mode_service=None,
    )
    out = svc.process("ch1", "p1", "look")
    assert out.public_narrative == "visibility handled"
