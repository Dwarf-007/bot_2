from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, Optional, Set, Tuple

Cell = Tuple[int, int]


@dataclass(frozen=True)
class TrueLosResult:
    anchor: Cell
    radius_cells: int
    visible_cells: Set[Cell]
    candidate_cells_count: int
    blocked_rays_count: int
    blocker_mode: str = "walls_and_closed_doors"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anchor": [int(self.anchor[0]), int(self.anchor[1])],
            "radius_cells": int(self.radius_cells),
            "visible_cells_count": len(self.visible_cells),
            "candidate_cells_count": int(self.candidate_cells_count),
            "blocked_rays_count": int(self.blocked_rays_count),
            "blocker_mode": self.blocker_mode,
        }


class TrueLosGridAdapter:
    """Conservative tile interpretation for True LOS.

    Intended semantics:
    - walls block sight;
    - closed doors block sight;
    - open floors/passages/known open doorways pass sight;
    - secret/hidden/concealed door cells should behave as wall unless another layer
      has already converted them to a revealed/open traversable cell.

    The adapter supports multiple grid styles from the current codebase:
    - grid.is_walkable(row, col)
    - grid.blocks_sight(row, col)
    - grid.token(row, col) / grid.get(row, col)
    - grid.cells / grid.tokens / grid.grid 2D arrays
    """

    PASS_PREFIXES = ("F", "S", "OPEN", "O", ".", "ROOM", "CORRIDOR")
    DOOR_PASS_PREFIXES = ("DO", "OPEN_DOOR", "OD")
    BLOCK_PREFIXES = ("W", "#", "X", "BLOCK", "WALL", "ROCK", "VOID")
    CLOSED_DOOR_PREFIXES = ("DC", "CLOSED_DOOR", "LOCKED_DOOR", "DL", "SECRET", "HIDDEN", "CONCEALED")

    def __init__(self, grid: Any = None) -> None:
        self.grid = grid
        self.rows, self.cols = self._size(grid)

    def in_bounds(self, row: int, col: int) -> bool:
        if self.rows is None or self.cols is None:
            return True
        return 0 <= int(row) < self.rows and 0 <= int(col) < self.cols

    def blocks_sight(self, row: int, col: int) -> bool:
        row = int(row)
        col = int(col)
        if not self.in_bounds(row, col):
            return True
        g = self.grid
        if g is None:
            return False

        fn = getattr(g, "blocks_sight", None)
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

        token = self.token(row, col)
        if token is not None:
            return self._token_blocks_sight(token)

        # Fallback: if it is not walkable, assume it blocks sight.
        for name in ("is_walkable", "walkable", "is_floor"):
            fn = getattr(g, name, None)
            if callable(fn):
                try:
                    return not bool(fn(row, col))
                except TypeError:
                    try:
                        return not bool(fn((row, col)))
                    except Exception:
                        pass
                except Exception:
                    pass
        return False

    def is_visible_target(self, row: int, col: int) -> bool:
        # Target cell itself should generally be passable/visible. If the target is
        # a wall/closed door, do not reveal it as floor. Door labels are handled by
        # text look systems, not by map cell reveal.
        return not self.blocks_sight(row, col)

    def token(self, row: int, col: int) -> Optional[str]:
        g = self.grid
        if g is None:
            return None
        for name in ("token", "get_token", "get"):
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

    def _token_blocks_sight(self, token: Any) -> bool:
        t = str(token or "").strip().upper()
        if not t:
            return True
        if t.startswith(self.CLOSED_DOOR_PREFIXES):
            return True
        if t.startswith(self.BLOCK_PREFIXES):
            return True
        if t.startswith(self.DOOR_PASS_PREFIXES):
            return False
        if t.startswith(self.PASS_PREFIXES):
            return False
        # Unknown token: prefer conservative blocking for LOS.
        return True

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


class TrueLosVisibilityEngine:
    """True line-of-sight visibility based on supercover line tracing.

    For each candidate target cell inside radius:
    1. build a supercover line from anchor to target;
    2. every intermediate cell must be transparent;
    3. target cell must be visible/passable;
    4. if open, add target to visible set.

    This is cheap for normal TTRPG radii. Even radius 20 is only ~1250 target
    cells, each with ~20 line steps.
    """

    def __init__(self, grid: Any = None) -> None:
        self.grid = TrueLosGridAdapter(grid)

    def compute(self, anchor: Cell, radius_cells: int, *, include_anchor: bool = True) -> TrueLosResult:
        radius = max(0, int(radius_cells or 0))
        ar, ac = int(anchor[0]), int(anchor[1])
        visible: Set[Cell] = set()
        candidates = 0
        blocked = 0

        if include_anchor and self.grid.in_bounds(ar, ac):
            visible.add((ar, ac))

        if radius <= 0:
            return TrueLosResult((ar, ac), radius, visible, 0, 0)

        for r in range(ar - radius, ar + radius + 1):
            for c in range(ac - radius, ac + radius + 1):
                if not self.grid.in_bounds(r, c):
                    continue
                if (r, c) == (ar, ac):
                    continue
                if math.hypot(r - ar, c - ac) > radius + 0.001:
                    continue
                candidates += 1
                if self._has_los((ar, ac), (r, c)):
                    visible.add((r, c))
                else:
                    blocked += 1

        return TrueLosResult((ar, ac), radius, visible, candidates, blocked)

    def _has_los(self, start: Cell, target: Cell) -> bool:
        line = list(self._supercover_line(start, target))
        if not line:
            return False
        # Intermediate blockers stop sight. Do not test start cell.
        for cell in line[1:-1]:
            if self.grid.blocks_sight(*cell):
                return False
        # Target cell should be a visible/open cell.
        return self.grid.is_visible_target(*target)

    def _supercover_line(self, start: Cell, end: Cell):
        """Supercover line between grid cells.

        Supercover includes cells touched by the ideal line, reducing corner-peeking
        compared to thin Bresenham.
        """
        y0, x0 = int(start[0]), int(start[1])
        y1, x1 = int(end[0]), int(end[1])
        dx = x1 - x0
        dy = y1 - y0
        nx = abs(dx)
        ny = abs(dy)
        sign_x = 1 if dx > 0 else -1 if dx < 0 else 0
        sign_y = 1 if dy > 0 else -1 if dy < 0 else 0

        x = x0
        y = y0
        yield (y, x)

        ix = iy = 0
        while ix < nx or iy < ny:
            # Compare next vertical/horizontal grid crossing.
            # If equal, advance both and include the diagonal touch.
            lhs = (1 + 2 * ix) * ny
            rhs = (1 + 2 * iy) * nx
            if lhs == rhs:
                x += sign_x
                y += sign_y
                ix += 1
                iy += 1
            elif lhs < rhs:
                x += sign_x
                ix += 1
            else:
                y += sign_y
                iy += 1
            yield (y, x)
