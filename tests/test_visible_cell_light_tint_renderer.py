from pathlib import Path
from PIL import Image
from services.visibility.fog_cell_renderer import FogCellRenderer


def test_visible_tint_renderer(tmp_path):
    src = tmp_path / "src.png"
    out = tmp_path / "out.png"
    Image.new("RGBA", (28, 28), (10, 10, 10, 255)).save(src)
    FogCellRenderer().render(src, {(0, 0)}, out, cell_size=14, visible_tint=True)
    assert out.exists()
