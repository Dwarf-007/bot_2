from types import SimpleNamespace

from models.runtime_mode import RuntimeMode
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
    def __init__(self, bundle=None, result=None):
        self.resolver = Resolver(bundle) if bundle is not None else None
        self.calls = 0
        self.result = result or {"handled": True, "ok": True, "text": "dungeon", "raw": {}}
    def try_handle(self, **kwargs):
        self.calls += 1
        return self.result


def test_router_detects_dungeon_from_bundle_and_handles():
    bundle = SimpleNamespace(visibility_available=True, map_available=True)
    adapter = Adapter(bundle=bundle)
    router = RuntimeModeRouter(runtime_mode_service=RuntimeModeService(), visibility_movement_adapter=adapter)
    result = router.try_handle_pre_llm(channel_repo=ChannelRepo({"campaign_id": "c1"}), channel_id="ch", player_id="p", campaign_id="c1", text="look")
    assert result.handled is True
    assert result.decision.mode == RuntimeMode.DUNGEON
    assert adapter.calls == 1


def test_router_campaign_mode_does_not_call_dungeon_adapter():
    adapter = Adapter(bundle=None)
    router = RuntimeModeRouter(runtime_mode_service=RuntimeModeService(), visibility_movement_adapter=adapter, allow_unknown_dungeon_probe=False)
    result = router.try_handle_pre_llm(channel_repo=ChannelRepo({"campaign_id": "c1", "mode": "campaign", "rag_available": True}), channel_id="ch", player_id="p", campaign_id="c1", text="hello")
    assert result.handled is False
    assert result.decision.mode == RuntimeMode.CAMPAIGN
    assert adapter.calls == 0
