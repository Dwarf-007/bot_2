from types import SimpleNamespace

from services.runtime_mode_router import RuntimeModeRouter
from services.runtime_mode_service import RuntimeModeService


class ChannelRepo:
    def __init__(self, state):
        self.state = state
    def get_state(self, channel_id):
        return self.state


class Resolver:
    def __init__(self, bundle):
        self.bundle = bundle
    def resolve(self, campaign_id):
        return self.bundle


class Adapter:
    def __init__(self, bundle=None):
        self.resolver = Resolver(bundle) if bundle is not None else None
        self.calls = 0
    def try_handle(self, **kwargs):
        self.calls += 1
        return {"handled": True, "ok": True, "text": "dungeon handled", "raw": {}}


def test_dungeon_mode_calls_adapter_for_mvp_command():
    bundle = SimpleNamespace(visibility_available=True, map_available=True)
    adapter = Adapter(bundle=bundle)
    router = RuntimeModeRouter(runtime_mode_service=RuntimeModeService(), visibility_movement_adapter=adapter)
    result = router.try_handle_pre_llm(channel_repo=ChannelRepo({"campaign_id": "c1", "mode": "dungeon"}), channel_id="ch", player_id="p", campaign_id="c1", text="look")
    assert result.handled is True
    assert adapter.calls == 1


def test_dungeon_mode_does_not_call_adapter_for_free_chat():
    bundle = SimpleNamespace(visibility_available=True, map_available=True)
    adapter = Adapter(bundle=bundle)
    router = RuntimeModeRouter(runtime_mode_service=RuntimeModeService(), visibility_movement_adapter=adapter)
    result = router.try_handle_pre_llm(channel_repo=ChannelRepo({"campaign_id": "c1", "mode": "dungeon"}), channel_id="ch", player_id="p", campaign_id="c1", text="beszélgetek a kereskedővel")
    assert result.handled is False
    assert result.skipped_reason == "not_dungeon_mvp_command"
    assert adapter.calls == 0
