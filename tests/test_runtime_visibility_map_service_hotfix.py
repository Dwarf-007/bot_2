import json
from pathlib import Path

from PIL import Image

from models.corridor_visibility_models import VisibilityPosition, VisibilityState
from services.runtime_visibility_map_service import RuntimeVisibilityMapService
from services.visibility.visibility_state_store import VisibilityStateStore


def test_runtime_visibility_map_service_imports_and_compiles():
    import services.runtime_visibility_map_service as mod
    assert hasattr(mod, "RuntimeVisibilityMapService")
    assert hasattr(mod, "RuntimeVisibilityMapResult")


def test_runtime_visibility_map_service_renders_local_and_full(tmp_path: Path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    source = bundle / "level_01_player_map.png"
    Image.new("RGBA", (70, 70), (200, 200, 200, 255)).save(source)
    (bundle / "fog_manifest.json").write_text(
        json.dumps({
            "levels": [
                {
                    "level": 1,
                    "cell_size": 14,
                    "players_map_image": str(source),
                }
            ]
        }),
        encoding="utf-8",
    )
    state = VisibilityState(
        campaign_id="c1",
        current=VisibilityPosition(node_id="s1", node_type="segment", level=1, segment_id="s1", cell=(1, 1)),
        visible_cells=[(1, 1), (1, 2), (2, 2)],
        explored_cells=[(0, 0), (1, 1)],
        visited_cells=[(1, 1)],
    )
    VisibilityStateStore(bundle / "visibility_runtime_state_ch1.json").save(state)

    svc = RuntimeVisibilityMapService(bundle, "c1")
    local = svc.render_for_channel("ch1", map_mode="local")
    assert local.ok is True
    assert local.output_file
    assert Path(local.output_file).exists()
    assert local.viewport_box is not None
    assert local.explored_cells_count >= local.visible_cells_count

    full = svc.render_for_channel("ch1", map_mode="full")
    assert full.ok is True
    assert full.output_file
    assert Path(full.output_file).exists()
    assert full.map_mode == "full"
