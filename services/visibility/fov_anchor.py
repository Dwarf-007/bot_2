from __future__ import annotations

import json
import math
from collections import deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

Cell = Tuple[int, int]


@dataclass(frozen=True)
class FovAnchor:
    row: int
    col: int
    source: str
    node_id: Optional[str] = None
    level: int = 1
    walkable: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GridWalkabilityAdapter:
    """Compatibility wrapper around DonjonVisibilityGrid-like objects."""

    DEFAULT_WALKABLE_PREFIXES = ("F", "D", "S")

    def __init__(self, grid: Any = None) -> None:
        self.grid = grid
        self.rows, self.cols = self._size(grid)

    def in_bounds(self, row: int, col: int) -> bool:
        if self.rows is None or self.cols is None:
            return True
        return 0 <= int(row) < self.rows and 0 <= int(col) < self.cols

    def is_walkable(self, row: int, col: int) -> bool:
        row = int(row)
        col = int(col)
        if not self.in_bounds(row, col):
            return False
        g = self.grid
        if g is None:
            return True
        for name in ("is_walkable", "walkable", "is_floor"):
            fn = getattr(g, name, None)
            if callable(fn):
                try:
                    return bool(fn(row, col))
                except TypeError:
                    try:
                        return bool(fn((row, col)))
                    except Exception:
                        pass
                except Exception:
                    pass
        tok = self.token(row, col)
        if tok is None:
            return False
        tok = str(tok).strip().upper()
        return bool(tok) and tok.startswith(self.DEFAULT_WALKABLE_PREFIXES)

    def token(self, row: int, col: int) -> Optional[str]:
        g = self.grid
        if g is None:
            return None
        for name in ("get", "token", "get_token"):
            fn = getattr(g, name, None)
            if callable(fn):
                try:
                    return fn(int(row), int(col))
                except TypeError:
                    try:
                        return fn((int(row), int(col)))
                    except Exception:
                        pass
                except Exception:
                    pass
        for attr in ("cells", "tokens", "grid"):
            data = getattr(g, attr, None)
            if isinstance(data, list):
                try:
                    return data[int(row)][int(col)]
                except Exception:
                    pass
        return None

    def nearest_walkable(self, cell: Cell, candidates: Iterable[Cell] | None = None, max_radius: int = 4) -> Optional[Cell]:
        r0, c0 = int(cell[0]), int(cell[1])
        if self.is_walkable(r0, c0):
            return (r0, c0)
        if candidates:
            parsed = []
            for item in candidates:
                try:
                    r, c = item
                    parsed.append((int(r), int(c)))
                except Exception:
                    pass
            parsed = [x for x in parsed if self.is_walkable(*x)]
            if parsed:
                parsed.sort(key=lambda x: abs(x[0] - r0) + abs(x[1] - c0))
                return parsed[0]
        for radius in range(1, max_radius + 1):
            found = []
            for r in range(r0 - radius, r0 + radius + 1):
                for c in range(c0 - radius, c0 + radius + 1):
                    if abs(r - r0) + abs(c - c0) > radius:
                        continue
                    if self.is_walkable(r, c):
                        found.append((r, c))
            if found:
                found.sort(key=lambda x: abs(x[0] - r0) + abs(x[1] - c0))
                return found[0]
        return None

    def _size(self, grid: Any) -> Tuple[Optional[int], Optional[int]]:
        if grid is None:
            return None, None
        for r_attr, c_attr in (("rows", "cols"), ("n_rows", "n_cols"), ("height", "width")):
            r = getattr(grid, r_attr, None)
            c = getattr(grid, c_attr, None)
            if isinstance(r, int) and isinstance(c, int):
                return r, c
        for attr in ("cells", "tokens", "grid"):
            data = getattr(grid, attr, None)
            if isinstance(data, list) and data:
                widths = [len(row) for row in data if isinstance(row, list)]
                return len(data), max(widths) if widths else None
        return None, None


class VisibilityGraphAccessor:
    """Read corridor_visibility_graph.json and expose segment cells/metadata."""

    def __init__(self, bundle_dir: str | Path) -> None:
        self.bundle_dir = Path(bundle_dir)
        self._graph: Optional[Dict[str, Any]] = None
        self._segments_by_id: Optional[Dict[str, Dict[str, Any]]] = None

    def graph(self) -> Dict[str, Any]:
        if self._graph is None:
            p = self.bundle_dir / "corridor_visibility_graph.json"
            try:
                self._graph = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
            except Exception:
                self._graph = {}
        return self._graph

    def segments_by_id(self) -> Dict[str, Dict[str, Any]]:
        if self._segments_by_id is not None:
            return self._segments_by_id
        data = self.graph().get("segments") if isinstance(self.graph(), dict) else None
        out: Dict[str, Dict[str, Any]] = {}
        if isinstance(data, dict):
            for sid, seg in data.items():
                if isinstance(seg, dict):
                    seg = dict(seg)
                    seg.setdefault("segment_id", sid)
                    out[str(sid)] = seg
        elif isinstance(data, list):
            for seg in data:
                if isinstance(seg, dict) and seg.get("segment_id"):
                    out[str(seg["segment_id"])] = seg
        self._segments_by_id = out
        return out

    def segment(self, segment_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not segment_id:
            return None
        return self.segments_by_id().get(str(segment_id))

    def current_segment_cells(self, segment_id: Optional[str]) -> list[Cell]:
        return self.cells_of(self.segment(segment_id))

    @staticmethod
    def cells_of(seg: Optional[Dict[str, Any]]) -> list[Cell]:
        out: list[Cell] = []
        if not isinstance(seg, dict):
            return out
        for cell in seg.get("cells") or []:
            try:
                r, c = cell
                out.append((int(r), int(c)))
            except Exception:
                pass
        return out


class FovAnchorResolver:
    """Resolve local-map anchor.

    Segment positions prefer current segment centroid over state.current.cell.
    """

    def __init__(self, bundle_dir: str | Path, grid: Any = None) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.walkability = GridWalkabilityAdapter(grid)
        self.graph = VisibilityGraphAccessor(bundle_dir)
        self._map_geometry: Optional[Dict[str, Any]] = None
        self._room_data: Optional[Dict[str, Any]] = None

    def resolve(self, state: Any, visible_cells: Iterable[Cell] | None = None) -> Optional[FovAnchor]:
        current = getattr(state, "current", None)
        level = int(getattr(current, "level", 1) or 1) if current else 1
        node_type = str(getattr(current, "node_type", "") or "") if current else ""
        node_id = getattr(current, "node_id", None) if current else None
        visible_list = list(visible_cells or [])
        segment_id = getattr(current, "segment_id", None) if current else None

        if node_type == "segment" or segment_id:
            seg_cells = self.graph.current_segment_cells(segment_id or node_id)
            cell = self._centroid(seg_cells) if seg_cells else None
            if cell:
                repaired = self.walkability.nearest_walkable(cell, candidates=seg_cells) or cell
                return FovAnchor(repaired[0], repaired[1], "segment.centroid", node_id=segment_id or node_id, level=level, walkable=self.walkability.is_walkable(*repaired))
            raw_cell = getattr(current, "cell", None) if current else None
            cell = self._cell_from_any(raw_cell)
            if cell:
                repaired = self.walkability.nearest_walkable(cell, candidates=visible_list) or cell
                return FovAnchor(repaired[0], repaired[1], "current.cell.segment_fallback", node_id=node_id, level=level, walkable=self.walkability.is_walkable(*repaired))

        raw_cell = getattr(current, "cell", None) if current else None
        cell = self._cell_from_any(raw_cell)
        if cell:
            repaired = self.walkability.nearest_walkable(cell, candidates=visible_list) or cell
            return FovAnchor(repaired[0], repaired[1], "current.cell", node_id=node_id, level=level, walkable=self.walkability.is_walkable(*repaired))

        room_id = getattr(current, "room_id", None) if current else None
        if room_id:
            cell = self._room_center(room_id)
            if cell:
                repaired = self.walkability.nearest_walkable(cell, candidates=visible_list) or cell
                return FovAnchor(repaired[0], repaired[1], "room.center", node_id=room_id, level=level, walkable=self.walkability.is_walkable(*repaired))

        if visible_list:
            cell = self._centroid(visible_list)
            repaired = self.walkability.nearest_walkable(cell, candidates=visible_list) or cell
            return FovAnchor(repaired[0], repaired[1], "visible_cells.centroid", node_id=node_id, level=level, walkable=self.walkability.is_walkable(*repaired))
        return None

    def _cell_from_any(self, value: Any) -> Optional[Cell]:
        if not value:
            return None
        try:
            r, c = value
            return int(r), int(c)
        except Exception:
            return None

    def _centroid(self, cells: Iterable[Cell]) -> Optional[Cell]:
        parsed: list[Cell] = []
        for cell in cells or []:
            cc = self._cell_from_any(cell)
            if cc:
                parsed.append(cc)
        if not parsed:
            return None
        return (round(sum(r for r, _ in parsed) / len(parsed)), round(sum(c for _, c in parsed) / len(parsed)))

    def _room_center(self, room_id: str) -> Optional[Cell]:
        for data in (self._load_map_geometry(), self._load_room_data()):
            rooms = data.get("rooms") if isinstance(data, dict) else None
            room = None
            if isinstance(rooms, dict):
                room = rooms.get(room_id)
            elif isinstance(rooms, list):
                for item in rooms:
                    if isinstance(item, dict) and item.get("room_id") == room_id:
                        room = item
                        break
            cell = self._center_from_room_like(room)
            if cell:
                return cell
        return None

    def _center_from_room_like(self, room: Any) -> Optional[Cell]:
        if not isinstance(room, dict):
            return None
        geom = room.get("geometry") if isinstance(room.get("geometry"), dict) else room
        if "north" in geom and "south" in geom and "west" in geom and "east" in geom:
            return int((geom["north"] + geom["south"]) / 2), int((geom["west"] + geom["east"]) / 2)
        if all(k in geom and geom.get(k) is not None for k in ("row", "col", "height", "width")):
            return int(geom["row"] + max(1, geom.get("height", 1)) / 2), int(geom["col"] + max(1, geom.get("width", 1)) / 2)
        return None

    def _load_map_geometry(self) -> Dict[str, Any]:
        if self._map_geometry is None:
            self._map_geometry = self._read_json("map_geometry.json")
        return self._map_geometry

    def _load_room_data(self) -> Dict[str, Any]:
        if self._room_data is None:
            self._room_data = self._read_json("room_data.json")
        return self._room_data

    def _read_json(self, name: str) -> Dict[str, Any]:
        p = self.bundle_dir / name
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}


class LOSFovCalculator:
    """Strict straight-line LOS. Useful for diagnostics; often too strict for narrow Donjon corridors."""

    def __init__(self, grid: Any = None) -> None:
        self.walkability = GridWalkabilityAdapter(grid)

    def compute(self, anchor: Cell, radius_cells: int, *, include_anchor: bool = True) -> Set[Cell]:
        radius = max(0, int(radius_cells or 0))
        ar, ac = int(anchor[0]), int(anchor[1])
        out: Set[Cell] = set()
        if include_anchor:
            out.add((ar, ac))
        if radius <= 0:
            return out
        for r in range(ar - radius, ar + radius + 1):
            for c in range(ac - radius, ac + radius + 1):
                if not self.walkability.in_bounds(r, c):
                    continue
                if math.hypot(r - ar, c - ac) > radius + 0.01:
                    continue
                if not self.walkability.is_walkable(r, c) and (r, c) != (ar, ac):
                    continue
                if self._has_line_of_sight((ar, ac), (r, c)):
                    out.add((r, c))
        return out

    def _has_line_of_sight(self, start: Cell, end: Cell) -> bool:
        cells = list(self._bresenham(start, end))
        if not cells:
            return False
        for cell in cells[1:]:
            if cell == end:
                return self.walkability.is_walkable(*cell) or cell == start
            if not self.walkability.is_walkable(*cell):
                return False
        return True

    def _bresenham(self, start: Cell, end: Cell):
        r0, c0 = start
        r1, c1 = end
        dr = abs(r1 - r0)
        dc = abs(c1 - c0)
        sr = 1 if r0 < r1 else -1
        sc = 1 if c0 < c1 else -1
        err = dc - dr
        r, c = r0, c0
        while True:
            yield (r, c)
            if r == r1 and c == c1:
                break
            e2 = 2 * err
            if e2 > -dr:
                err -= dr
                c += sc
            if e2 < dc:
                err += dc
                r += sr


class CorridorGraphFovCalculator:
    """Small expansion following corridor visibility graph cells."""

    def __init__(self, bundle_dir: str | Path, grid: Any = None) -> None:
        self.graph = VisibilityGraphAccessor(bundle_dir)
        self.walkability = GridWalkabilityAdapter(grid)

    def compute(self, start_segment_id: Optional[str], anchor: Cell, radius_cells: int, max_hops: int = 2) -> Set[Cell]:
        if not start_segment_id:
            return set()
        segments = self.graph.segments_by_id()
        if start_segment_id not in segments:
            return set()
        radius = max(0, int(radius_cells or 0))
        ar, ac = int(anchor[0]), int(anchor[1])
        out: Set[Cell] = set()
        seen: Set[str] = set()
        queue = deque([(str(start_segment_id), 0)])
        while queue:
            sid, hops = queue.popleft()
            if sid in seen or hops > max_hops:
                continue
            seen.add(sid)
            seg = segments.get(sid) or {}
            for cell in self.graph.cells_of(seg):
                r, c = cell
                if math.hypot(r - ar, c - ac) <= radius + 0.01:
                    out.add((r, c))
            for next_sid in seg.get("connected_segments") or []:
                if str(next_sid) not in seen:
                    queue.append((str(next_sid), hops + 1))
        return out


class HybridCorridorLightCalculator:
    """Segment-seed BFS light spread for local maps.

    This is the player-facing default. Instead of starting from only a single anchor
    cell, the light spread starts from all cells of the current corridor segment.
    That makes the visible area closer to tabletop expectations: if the party is in
    a corridor segment, that segment is the seed for torch/lantern visibility and
    nearby unvisited walkable corridor cells can become visible.
    """

    def __init__(self, bundle_dir: str | Path, grid: Any = None) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.walkability = GridWalkabilityAdapter(grid)
        self.graph = VisibilityGraphAccessor(bundle_dir)
        self.graph_calc = CorridorGraphFovCalculator(bundle_dir, grid=grid)

    def segment_seed_cells(self, start_segment_id: Optional[str], anchor: Cell) -> Set[Cell]:
        seeds: Set[Cell] = set()
        if start_segment_id:
            for cell in self.graph.current_segment_cells(start_segment_id):
                if self.walkability.is_walkable(*cell):
                    seeds.add(cell)
                else:
                    # Segment graph cells are usually meaningful even if TSV tokenization differs.
                    seeds.add(cell)
        if not seeds:
            repaired = self.walkability.nearest_walkable(anchor)
            seeds.add(repaired or (int(anchor[0]), int(anchor[1])))
        return seeds

    def compute(self, start_segment_id: Optional[str], anchor: Cell, radius_cells: int, max_graph_hops: int = 2) -> tuple[Set[Cell], Set[Cell]]:
        radius = max(0, int(radius_cells or 0))
        seeds = self.segment_seed_cells(start_segment_id, anchor)
        out: Set[Cell] = set(seeds)
        queue = deque([(cell, 0) for cell in seeds])
        seen: Set[Cell] = set(seeds)
        while queue:
            (r, c), dist = queue.popleft()
            if dist >= radius:
                continue
            for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                n = (nr, nc)
                if n in seen:
                    continue
                if not self.walkability.in_bounds(nr, nc):
                    continue
                if not self.walkability.is_walkable(nr, nc):
                    continue
                seen.add(n)
                out.add(n)
                queue.append((n, dist + 1))
        out |= self.graph_calc.compute(start_segment_id, anchor, radius, max_hops=max_graph_hops)
        return out, seeds
