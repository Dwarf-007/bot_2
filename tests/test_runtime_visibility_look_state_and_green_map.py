
from types import SimpleNamespace

from services.dungeon_runtime_green_path_smoke_service import DungeonRuntimeGreenPathSmokeService
from services.runtime_visibility_command_handler import RuntimeVisibilityCommandHandler


class FakeStateService:
    def __init__(self):
        self.saved = None
        self.raw_state = None
    def state_from_raw(self, raw):
        return self.raw_state
    def save_state(self, bundle, channel_id, state):
        self.saved = state
    def migrate_state(self, state):
        return state


class FakeFormatter:
    def format_look(self, raw):
        return "look formatted"
    def format_move(self, raw):
        return "move formatted"
    def format_secret_search(self, raw):
        return raw.get("message", "")


class FakeEngine:
    def __init__(self, raw):
        self.raw = raw
    def look(self, state):
        return self.raw


def test_handle_look_saves_state_from_raw_when_present():
    state_service = FakeStateService()
    original = SimpleNamespace(name="original")
    derived = SimpleNamespace(name="derived", visible_cells=[(1, 1)])
    state_service.raw_state = derived
    handler = RuntimeVisibilityCommandHandler(state_service=state_service, formatter=FakeFormatter())
    bundle = SimpleNamespace(bundle_dir=".", campaign_id="c1")
    raw = {"ok": True, "state": {"visible_cells": [[1, 1]]}, "look": {}}
    result = handler.handle_look(bundle=bundle, channel_id="ch", engine=FakeEngine(raw), state=original)
    assert result["ok"] is True
    assert state_service.saved is derived


def test_handle_look_falls_back_to_original_state_when_raw_has_no_state():
    state_service = FakeStateService()
    original = SimpleNamespace(name="original")
    handler = RuntimeVisibilityCommandHandler(state_service=state_service, formatter=FakeFormatter())
    bundle = SimpleNamespace(bundle_dir=".", campaign_id="c1")
    raw = {"ok": True, "look": {}}
    handler.handle_look(bundle=bundle, channel_id="ch", engine=FakeEngine(raw), state=original)
    assert state_service.saved is original


class Out:
    def __init__(self, text):
        self.public_narrative = text


class FakeGTS:
    def __init__(self, outputs):
        self.outputs = list(outputs)
    def process(self, *args, **kwargs):
        return Out(self.outputs.pop(0))


def test_green_path_map_missing_visible_cells_is_failure():
    svc = DungeonRuntimeGreenPathSmokeService(FakeGTS(["look ok", "Nincs látható cella a térkép rendereléséhez.", "move ok", "back ok", "full map ok", "search ok"]))
    result = svc.run(channel_id="ch", player_id="p", campaign_id_override="tenebrous")
    assert result.ok is False
    map_step = [s for s in result.steps if s.name == "map"][0]
    assert map_step.ok is False
    assert "Forbidden green-path marker" in map_step.detected_issue
