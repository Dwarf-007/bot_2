from models.corridor_visibility_models import VisibilityPosition, VisibilityState
from services.visibility.fog_of_war_policy import FogCellState, FogOfWarPolicy


def test_apply_visible_cells_merges_into_explored_cells():
    state = VisibilityState(
        campaign_id="c1",
        current=VisibilityPosition(node_id="s1", node_type="segment", level=1, segment_id="s1", cell=(5, 5)),
        explored_cells=[(1, 1)],
    )
    FogOfWarPolicy.apply_visible_cells(state, [(5, 5), (5, 6)])
    assert set(state.visible_cells) == {(5, 5), (5, 6)}
    assert set(state.explored_cells) == {(1, 1), (5, 5), (5, 6)}


def test_mark_current_cell_visited():
    state = VisibilityState(
        campaign_id="c1",
        current=VisibilityPosition(node_id="s1", node_type="segment", level=1, segment_id="s1", cell=(5, 5)),
    )
    FogOfWarPolicy.mark_current_cell_visited(state)
    assert set(state.visited_cells) == {(5, 5)}


def test_snapshot_cell_states():
    state = VisibilityState(
        campaign_id="c1",
        current=VisibilityPosition(node_id="s1", node_type="segment", level=1, segment_id="s1", cell=(5, 5)),
        visible_cells=[(5, 5), (5, 6)],
        explored_cells=[(1, 1), (5, 5), (5, 6)],
        visited_cells=[(5, 5)],
    )
    snap = FogOfWarPolicy.snapshot(state)
    assert snap.cell_state((5, 5)) == FogCellState.CURRENT
    assert snap.cell_state((5, 6)) == FogCellState.VISIBLE
    assert snap.cell_state((1, 1)) == FogCellState.EXPLORED
    assert snap.cell_state((9, 9)) == FogCellState.UNKNOWN
