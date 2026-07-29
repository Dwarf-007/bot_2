from types import SimpleNamespace

from models.corridor_visibility_models import VisibilityPosition, VisibilityState
from services.runtime_visibility_command_handler import RuntimeVisibilityCommandHandler
from services.runtime_visibility_intents import RuntimeVisibilityIntent


class DummyStateService:
    def __init__(self):
        self.saved = False
        self.state = VisibilityState(
            campaign_id="c1",
            current=VisibilityPosition(node_id="r1", node_type="room", level=1, room_id="r1"),
            visited_rooms=["r1"],
        )

    def load_or_init_state(self, bundle, channel_id, player_id=""):
        return self.state

    def save_state(self, bundle, channel_id, state):
        self.saved = True
        self.state = state

    def state_from_raw(self, raw):
        return None

    def migrate_state(self, state):
        if not hasattr(state, "path_history") or state.path_history is None:
            state.path_history = []
        return state


class DummyFormatter:
    def format_look(self, raw):
        return "LOOK_FORMATTED"

    def format_move(self, raw):
        return "MOVE_FORMATTED"

    def format_secret_search(self, raw):
        return "SECRET_FORMATTED"


class DummyEngine:
    def look(self, state):
        return {"ok": True, "look": {"visible_cells_count": 0}}

    def move(self, state, direction, choice=None):
        return {"ok": True, "state": state.to_dict(), "look": {}}


def test_handle_look_saves_state(monkeypatch):
    svc = DummyStateService()
    handler = RuntimeVisibilityCommandHandler(state_service=svc, formatter=DummyFormatter())
    monkeypatch.setattr(handler, "create_engine", lambda bundle: DummyEngine())
    bundle = SimpleNamespace(bundle_dir=".", campaign_id="c1")
    result = handler.handle(bundle=bundle, channel_id="ch1", player_id="p1", intent=RuntimeVisibilityIntent("LOOK"))
    assert result["handled"] is True
    assert result["ok"] is True
    assert result["text"] == "LOOK_FORMATTED"
    assert svc.saved is True


def test_handle_move_saves_state(monkeypatch):
    svc = DummyStateService()
    handler = RuntimeVisibilityCommandHandler(state_service=svc, formatter=DummyFormatter())
    monkeypatch.setattr(handler, "create_engine", lambda bundle: DummyEngine())
    bundle = SimpleNamespace(bundle_dir=".", campaign_id="c1")
    result = handler.handle(bundle=bundle, channel_id="ch1", player_id="p1", intent=RuntimeVisibilityIntent("MOVE", direction="north"))
    assert result["handled"] is True
    assert result["ok"] is True
    assert result["text"] == "MOVE_FORMATTED"
    assert svc.saved is True
