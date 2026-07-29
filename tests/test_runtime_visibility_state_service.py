from pathlib import Path
from types import SimpleNamespace

from services.runtime_visibility_state_service import RuntimeVisibilityStateService
from models.corridor_visibility_models import VisibilityPosition, VisibilityState


def bundle(tmp_path: Path):
    d = tmp_path / "bundle"
    d.mkdir()
    return SimpleNamespace(bundle_dir=d, campaign_id="c1")


def test_state_file_is_channel_scoped(tmp_path: Path):
    b = bundle(tmp_path)
    svc = RuntimeVisibilityStateService()
    assert svc.state_file(b, "abc/def").name == "visibility_runtime_state_abc_def.json"


def test_load_or_init_creates_state(tmp_path: Path):
    b = bundle(tmp_path)
    svc = RuntimeVisibilityStateService()
    state = svc.load_or_init_state(b, "ch1", "p1")
    assert state.campaign_id == "c1"
    assert state.visited_rooms
    assert svc.state_file(b, "ch1").exists()


def test_migrate_state_adds_fow_fields():
    state = VisibilityState(
        campaign_id="c1",
        current=VisibilityPosition(node_id="s1", node_type="segment", level=1, segment_id="s1", cell=(1, 2)),
        visible_cells=[(1, 2), (1, 3)],
    )
    # simulate older object shape
    state.explored_cells = []
    state.visited_cells = []
    migrated = RuntimeVisibilityStateService().migrate_state(state)
    assert set(migrated.explored_cells) == {(1, 2), (1, 3)}
    assert set(migrated.visited_cells) == {(1, 2)}


def test_state_from_raw_extracts_and_migrates():
    raw = {
        "state": {
            "campaign_id": "c1",
            "current": {"node_id": "s1", "node_type": "segment", "level": 1, "segment_id": "s1", "cell": [3, 4]},
            "visible_cells": [[3, 4]],
            "visited_segments": ["s1"],
        }
    }
    state = RuntimeVisibilityStateService().state_from_raw(raw)
    assert state is not None
    assert set(state.explored_cells) == {(3, 4)}
    assert set(state.visited_cells) == {(3, 4)}
