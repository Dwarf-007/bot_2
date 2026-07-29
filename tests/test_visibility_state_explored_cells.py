from models.corridor_visibility_models import VisibilityPosition, VisibilityState


def test_from_dict_migrates_old_state_without_explored_or_visited_cells():
    old = {
        "campaign_id": "c1",
        "current": {"node_id": "s1", "node_type": "segment", "level": 1, "segment_id": "s1", "cell": [10, 20]},
        "visited_rooms": [],
        "visited_segments": ["s1"],
        "visible_cells": [[10, 20], [10, 21]],
        "path_history": [],
    }
    state = VisibilityState.from_dict(old)
    assert set(state.visible_cells) == {(10, 20), (10, 21)}
    assert set(state.explored_cells) == {(10, 20), (10, 21)}
    assert set(state.visited_cells) == {(10, 20)}


def test_to_dict_writes_explored_and_visited_cells():
    state = VisibilityState(
        campaign_id="c1",
        current=VisibilityPosition(node_id="s1", node_type="segment", level=1, segment_id="s1", cell=(1, 2)),
        visible_cells=[(1, 2)],
        explored_cells=[(1, 2), (1, 3)],
        visited_cells=[(1, 2)],
    )
    data = state.to_dict()
    assert data["visible_cells"] == [[1, 2]]
    assert data["explored_cells"] == [[1, 2], [1, 3]]
    assert data["visited_cells"] == [[1, 2]]


def test_record_visible_cells_merges_explored_cells_monotonically():
    state = VisibilityState(
        campaign_id="c1",
        current=VisibilityPosition(node_id="s1", node_type="segment", level=1, segment_id="s1", cell=(2, 2)),
        visible_cells=[(1, 1)],
        explored_cells=[(1, 1)],
    )
    state.record_visible_cells([(2, 2), (2, 3)])
    assert set(state.visible_cells) == {(2, 2), (2, 3)}
    assert set(state.explored_cells) == {(1, 1), (2, 2), (2, 3)}
