from __future__ import annotations

from collections import deque
from typing import Iterable, Optional, Set, Tuple

from services.visibility.donjon_visibility_grid import DonjonVisibilityGrid
from services.visibility.vision_profile import VisionProfile

Cell = Tuple[int, int]


class VisibleCellExpander:
    """Expands visible cells according to a VisionProfile.

    MVP rules:
    - Expansion is bounded by walkable cells in the TSV grid when a grid exists.
    - Expansion uses 4-neighbor BFS and therefore naturally follows corridors
      better than a square flood fill.
    - This does NOT yet implement full line-of-sight ray casting. The flags
      respect_corners/respect_walls are kept in the profile so later strict LOS
      can be introduced without changing callers.
    """

    def expand(
        self,
        base_cells: Iterable[Cell],
        profile: VisionProfile,
        *,
        grid: Optional[DonjonVisibilityGrid] = None,
        current_cell: Optional[Cell] = None,
    ) -> Set[Cell]:
        base: Set[Cell] = self._normalise(base_cells)
        if current_cell is not None:
            try:
                base.add((int(current_cell[0]), int(current_cell[1])))
            except Exception:
                pass

        radius = max(
            int(profile.bright_radius_cells or 0),
            int(profile.dim_radius_cells or 0) if profile.reveal_dim_as_seen else 0,
            int(profile.darkvision_radius_cells or 0),
        )
        if radius <= 0 or not base:
            return base

        if grid is None:
            return self._expand_manhattan_unbounded(base, radius)
        return self._expand_walkable_bfs(base, radius, grid)

    def _expand_walkable_bfs(self, seeds: Set[Cell], radius: int, grid: DonjonVisibilityGrid) -> Set[Cell]:
        out: Set[Cell] = set(seeds)
        q = deque((cell, 0) for cell in seeds)
        seen: Set[Cell] = set(seeds)
        while q:
            (r, c), dist = q.popleft()
            if dist >= radius:
                continue
            for nr, nc in grid.neighbors4(r, c):
                if (nr, nc) in seen:
                    continue
                if not grid.is_walkable(nr, nc):
                    continue
                seen.add((nr, nc))
                out.add((nr, nc))
                q.append(((nr, nc), dist + 1))
        return out

    def _expand_manhattan_unbounded(self, seeds: Set[Cell], radius: int) -> Set[Cell]:
        out: Set[Cell] = set(seeds)
        for r, c in seeds:
            for dr in range(-radius, radius + 1):
                remain = radius - abs(dr)
                for dc in range(-remain, remain + 1):
                    out.add((r + dr, c + dc))
        return {(r, c) for r, c in out if r >= 0 and c >= 0}

    @staticmethod
    def _normalise(cells: Iterable[Cell]) -> Set[Cell]:
        out: Set[Cell] = set()
        for raw in cells or []:
            try:
                r, c = raw
                out.add((int(r), int(c)))
            except Exception:
                continue
        return out
