from pathlib import Path
from types import SimpleNamespace

from services.runtime_visibility_command_handler import RuntimeVisibilityCommandHandler


class FakeStateService:
    def save_state(self, *args, **kwargs):
        pass


class FakeFormatter:
    def format_secret_search(self, raw):
        return raw.get("message", "")


class EngineBundleOnly:
    def __init__(self, bundle_dir):
        self.bundle_dir = bundle_dir
    def search_room(self, **kwargs):
        return {"ok": True, "found": True, "message": "found secret"}


class EnginePathThenStore:
    def __init__(self, bundle_dir, state_store):
        self.bundle_dir = bundle_dir
        self.state_store = state_store
    def search_room(self, **kwargs):
        return {"ok": True, "found": False, "message": "searched"}


class EngineRejectsStoreAsPath:
    def __init__(self, path_like):
        if not isinstance(path_like, (str, Path)):
            raise TypeError("argument should be a str or an os.PathLike object")
    def search_room(self, **kwargs):
        return {"ok": True, "found": False, "message": "searched path"}


def test_construct_secret_discovery_engine_prefers_path_based_constructor(tmp_path: Path):
    handler = RuntimeVisibilityCommandHandler()
    engine = handler._construct_secret_discovery_engine(EngineBundleOnly, bundle_dir=tmp_path, store=object())
    assert isinstance(engine, EngineBundleOnly)
    assert Path(engine.bundle_dir) == tmp_path


def test_construct_secret_discovery_engine_supports_bundle_and_store(tmp_path: Path):
    handler = RuntimeVisibilityCommandHandler()
    store = object()
    engine = handler._construct_secret_discovery_engine(EnginePathThenStore, bundle_dir=tmp_path, store=store)
    assert isinstance(engine, EnginePathThenStore)
    assert engine.state_store is store


def test_construct_secret_discovery_engine_does_not_pass_store_as_only_path(tmp_path: Path):
    handler = RuntimeVisibilityCommandHandler()
    engine = handler._construct_secret_discovery_engine(EngineRejectsStoreAsPath, bundle_dir=tmp_path, store=object())
    assert isinstance(engine, EngineRejectsStoreAsPath)


def test_search_secret_not_in_room_is_player_safe():
    handler = RuntimeVisibilityCommandHandler(state_service=FakeStateService(), formatter=FakeFormatter())
    state = SimpleNamespace(current=SimpleNamespace(room_id=None, segment_id="s1"))
    bundle = SimpleNamespace(bundle_dir=Path("."), campaign_id="c1")
    raw = handler.search_secret(bundle, state)
    assert raw["ok"] is True
    assert raw["found"] is False
    assert raw["reason"] == "not_in_room"
    assert "visibility runtime hibát" not in raw["message"].lower()


def test_call_secret_discovery_api_normalises_dict_result():
    handler = RuntimeVisibilityCommandHandler()
    engine = EngineBundleOnly(".")
    result = handler._call_secret_discovery_api(engine, current_room="r1")
    assert result["ok"] is True
    assert result["found"] is True
    assert result["message"] == "found secret"
