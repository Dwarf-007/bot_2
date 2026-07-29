"""
SERVICES/VISIBILITY/FOG_CELL_RENDERER.PY

Sprint 10.4 update: 3-state Fog-of-War renderer.

Backward compatible:
- old call style still works: render(source_map, cells, output_file, ...)
- new call style supports: visible_cells + explored_cells

States:
- UNKNOWN: covered by strong fog
- EXPLORED: dimmed/desaturated visibility
- VISIBLE: clear/bright visibility
- CURRENT: marked/highlighted current cell
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Set, Tuple

from PIL import Image, ImageDraw, ImageEnhance

Cell = Tuple[int, int]
RGBA = Tuple[int, int, int, int]


class FogCellRenderer:
    """Cell-level fog overlay renderer for Donjon player maps."""

    def render(
        self,
        source_map: str | Path,
        visible_cells: Iterable[Cell],
        output_file: str | Path,
        *,
        explored_cells: Optional[Iterable[Cell]] = None,
        cell_size: int = 14,
        fog_alpha: int = 252,
        explored_alpha: int = 145,
        reveal_padding: int = 0,
        draw_cell_outline: bool = False,
        current_cell: Optional[Cell] = None,
        current_cell_outline: RGBA = (255, 220, 80, 255),
    ) -> str:
        """Render a 3-state FOW image.

        Args:
            source_map: Input PNG/JPG map.
            visible_cells: Currently visible cells. These are rendered clear.
            output_file: Output PNG path.
            explored_cells: Previously seen cells. These are rendered dimmed.
                If omitted, the renderer behaves like the old renderer and treats
                visible_cells as the only revealed set.
            cell_size: Pixel size of one grid cell.
            fog_alpha: Alpha for unknown cells.
            explored_alpha: Alpha for explored-but-not-visible cells.
            reveal_padding: Extra pixel padding around revealed rectangles.
            draw_cell_outline: Optional debug outlines.
            current_cell: Optional current party/anchor cell marker.

        Returns:
            Output file path as string.
        """
        src = Path(source_map)
        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)

        img = Image.open(src).convert("RGBA")
        width, height = img.size
        cell = max(1, int(cell_size or 14))
        pad = max(0, int(reveal_padding or 0))

        visible: Set[Cell] = self._normalize_cells(visible_cells)
        explored: Set[Cell] = self._normalize_cells(explored_cells) if explored_cells is not None else set(visible)
        explored |= visible

        # Start from a fully fogged image.
        fogged = Image.new("RGBA", (width, height), (0, 0, 0, self._clamp_alpha(fog_alpha)))
        result = Image.alpha_composite(img, fogged)

        # EXPLORED cells: paste a dimmed/desaturated version of the original map.
        dimmed = ImageEnhance.Color(img).enhance(0.25)
        dimmed = ImageEnhance.Brightness(dimmed).enhance(0.55)
        explored_overlay = Image.new("RGBA", (width, height), (0, 0, 0, self._clamp_alpha(explored_alpha)))
        dimmed = Image.alpha_composite(dimmed, explored_overlay)

        for rc in sorted(explored - visible):
            box = self._cell_box(rc, cell, width, height, pad)
            if box:
                result.paste(dimmed.crop(box), box)

        # VISIBLE cells: paste original map cells back cleanly.
        for rc in sorted(visible):
            box = self._cell_box(rc, cell, width, height, pad)
            if box:
                result.paste(img.crop(box), box)

        draw = ImageDraw.Draw(result)
        if draw_cell_outline:
            for rc in sorted(explored):
                box = self._cell_box(rc, cell, width, height, 0)
                if box:
                    color = (80, 80, 80, 180) if rc not in visible else (255, 255, 255, 210)
                    draw.rectangle((box[0], box[1], box[2] - 1, box[3] - 1), outline=color, width=1)

        if current_cell is not None:
            box = self._cell_box(current_cell, cell, width, height, 0)
            if box:
                draw.rectangle((box[0], box[1], box[2] - 1, box[3] - 1), outline=current_cell_outline, width=max(2, cell // 5))

        result.save(out)
        return str(out)

    @staticmethod
    def _clamp_alpha(value: int) -> int:
        return max(0, min(255, int(value)))

    @staticmethod
    def _normalize_cells(cells: Optional[Iterable[Cell]]) -> Set[Cell]:
        out: Set[Cell] = set()
        for item in cells or []:
            try:
                r, c = item
                out.add((int(r), int(c)))
            except Exception:
                continue
        return out

    @staticmethod
    def _cell_box(cell: Cell, cell_size: int, width: int, height: int, padding: int = 0):
        try:
            r, c = int(cell[0]), int(cell[1])
        except Exception:
            return None
        x0 = max(0, c * cell_size - padding)
        y0 = max(0, r * cell_size - padding)
        x1 = min(width, (c + 1) * cell_size + padding)
        y1 = min(height, (r + 1) * cell_size + padding)
        if x1 <= x0 or y1 <= y0:
            return None
        return int(x0), int(y0), int(x1), int(y1)
