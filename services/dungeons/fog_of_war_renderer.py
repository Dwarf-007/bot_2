"""
SERVICES/DUNGEONS/FOG_OF_WAR_RENDERER.PY

First-pass Fog-of-War renderer.
It overlays darkness on a Donjon map and reveals visited rooms by their room
bounding boxes from map_geometry.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

try:
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None


class FogOfWarRenderer:
    def render(
        self,
        map_geometry_file: str | Path,
        level: int,
        visited_room_ids: Iterable[str],
        output_file: str | Path,
        current_room_id: Optional[str] = None,
        show_adjacent: bool = False,
        graph_file: str | Path | None = None,
    ) -> str:
        if Image is None:
            raise RuntimeError("Pillow is required for FogOfWarRenderer")
        geometry = json.loads(Path(map_geometry_file).read_text(encoding="utf-8"))
        level_asset = next((x for x in geometry.get("levels", []) if int(x.get("level")) == int(level)), None)
        if not level_asset or not level_asset.get("players_map_image"):
            raise FileNotFoundError(f"No players_map_image found for level {level}")
        map_path = Path(level_asset["players_map_image"])
        if not map_path.exists():
            raise FileNotFoundError(str(map_path))

        visited = set(visited_room_ids)
        reveal = set(visited)
        if show_adjacent and graph_file:
            reveal |= self._adjacent_rooms(graph_file, visited)

        img = Image.open(map_path).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 225))
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        cell_size = int(level_asset.get("cell_size") or 14)

        for room in geometry.get("rooms", []):
            if int(room.get("level")) != int(level):
                continue
            room_id = room.get("room_id")
            if room_id not in reveal:
                continue
            west = int(room.get("west") if room.get("west") is not None else room.get("col") or 0) * cell_size
            east = int(room.get("east") if room.get("east") is not None else room.get("col") or 0) * cell_size
            north = int(room.get("north") if room.get("north") is not None else room.get("row") or 0) * cell_size
            south = int(room.get("south") if room.get("south") is not None else room.get("row") or 0) * cell_size
            pad = cell_size
            draw.rectangle([max(0, west - pad), max(0, north - pad), min(img.size[0], east + pad), min(img.size[1], south + pad)], fill=255)

        revealed = Image.composite(img, overlay, mask)
        if current_room_id:
            self._draw_current_marker(revealed, geometry, level, current_room_id, cell_size)
        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        revealed.save(out)
        return str(out)

    @staticmethod
    def _adjacent_rooms(graph_file: str | Path, visited: set[str]) -> set[str]:
        graph = json.loads(Path(graph_file).read_text(encoding="utf-8"))
        result = set()
        for edge in graph.get("edges", []):
            if edge.get("from_room_id") in visited:
                result.add(edge.get("to_room_id"))
        return {x for x in result if x}

    @staticmethod
    def _draw_current_marker(img, geometry: dict, level: int, room_id: str, cell_size: int) -> None:
        draw = ImageDraw.Draw(img)
        room = next((r for r in geometry.get("rooms", []) if r.get("room_id") == room_id and int(r.get("level")) == int(level)), None)
        if not room:
            return
        west = int(room.get("west") if room.get("west") is not None else room.get("col") or 0) * cell_size
        east = int(room.get("east") if room.get("east") is not None else room.get("col") or 0) * cell_size
        north = int(room.get("north") if room.get("north") is not None else room.get("row") or 0) * cell_size
        south = int(room.get("south") if room.get("south") is not None else room.get("row") or 0) * cell_size
        draw.rectangle([west, north, east, south], outline=(255, 0, 0, 255), width=max(3, cell_size // 3))
