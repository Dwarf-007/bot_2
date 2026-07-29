import json
from pathlib import Path

from services.dungeon_runtime_fow_validator import DungeonRuntimeFowValidator


def valid_state():
    return {
        "campaign_id": "tenebrous",
        "current": {
            "node_id": "s1",
            "node_type": "segment",
            "level": 1,
            "room_id": None,
            "segment_id": "s1",
            "cell": [3, 4],
        },
        "visited_rooms": [],
        "visited_segments": ["s1"],
        "visible_cells": [[3, 4], [3, 5]],
        "explored_cells": [[3, 4], [3, 5], [2, 5]],
        "visited_cells": [[3, 4]],
        "path_history": [{"node_id": "s0", "node_type": "segment", "level": 1, "segment_id": "s0", "cell": [3, 3]}],
    }


def test_fow_validator_accepts_valid_state_dict():
    result = DungeonRuntimeFowValidator().validate_state_dict(valid_state(), channel_id="ch")
    assert result.ok is True
    assert result.visible_cells_count == 2
    assert result.explored_cells_count == 3
    assert result.path_history_count == 1


def test_fow_validator_rejects_visible_not_in_explored():
    data = valid_state()
    data["explored_cells"] = [[3, 4]]
    result = DungeonRuntimeFowValidator().validate_state_dict(data)
    assert result.ok is False
    failed = [c for c in result.checks if c.name == "explored_contains_visible"][0]
    assert failed.ok is False
    assert failed.details["missing_count"] == 1


def test_fow_validator_rejects_empty_visible_by_default():
    data = valid_state()
    data["visible_cells"] = []
    result = DungeonRuntimeFowValidator().validate_state_dict(data)
    assert result.ok is False
    assert [c for c in result.checks if c.name == "visible_cells_non_empty"][0].ok is False


def test_fow_validator_can_read_file(tmp_path: Path):
    p = tmp_path / "state.json"
    p.write_text(json.dumps(valid_state(), ensure_ascii=False), encoding="utf-8")
    result = DungeonRuntimeFowValidator().validate_state_file(state_file=p, channel_id="ch")
    assert result.ok is True
    assert result.state_file == str(p)


def test_segment_current_cell_requirement():
    data = valid_state()
    data["current"]["cell"] = None
    result = DungeonRuntimeFowValidator().validate_state_dict(data, require_current_cell_when_segment=True)
    assert result.ok is False
    assert [c for c in result.checks if c.name == "segment_current_cell_present"][0].ok is False
