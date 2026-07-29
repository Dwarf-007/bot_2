from pathlib import Path
from PIL import Image
from services.visibility.fog_cell_renderer import FogCellRenderer


def test_fog_cell_renderer_supports_visible_and_explored_cells(tmp_path: Path):
    src = tmp_path / "map.png"
    out = tmp_path / "out.png"
    Image.new("RGBA", (42, 14), (200, 200, 200, 255)).save(src)

    rendered = FogCellRenderer().render(
        src,
        visible_cells={(0, 0)},
        explored_cells={(0, 0), (0, 1)},
        output_file=out,
        cell_size=14,
        fog_alpha=250,
        explored_alpha=130,
        current_cell=(0, 0),
    )

    assert Path(rendered).exists()
    img = Image.open(out).convert("RGBA")
    visible_px = img.getpixel((7, 7))
    explored_px = img.getpixel((21, 7))
    unknown_px = img.getpixel((35, 7))
    assert visible_px != unknown_px
    assert explored_px != unknown_px
    assert visible_px != explored_px
