"""
SERVICES/RUNTIME_VISIBILITY_MAP_SERVICE.PY

Sprint 12.2 - Map Runtime Syntax Hotfix.

Fixes the real smoke failure:
    "unterminated string literal ... runtime_visibility_map_service.py"

This replacement is intentionally syntax-clean and conservative:
- loads channel-scoped VisibilityState
- resolves player map image from fog_manifest.json / map_geometry.json / PNG fallback
- renders 3-state FOW through FogCellRenderer
- supports local viewport and full map modes
- persists newly visible cells into explored_cells
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

from services.visibility.fog_cell_renderer import FogCellRenderer
from services.visibility.visibility_state_store import VisibilityStateStore

try:  # Sprint 10.3+
    from services.visibility.fog_of_war_policy import FogOfWarPolicy
except Exception:  # pragma: no cover - compatibility with older installs
    FogOfWarPolicy = None  # type: ignore

Cell = Tuple[int, int]


@dataclass
class RuntimeVisibilityMapResult:
    ok: bool
    message: str
    output_file: Optional[str] = None
    source_map: Optional[str] = None
    level: Optional[int] = None
    map_mode: str = "local"
    visible_cells_count: int = 0
    explored_cells_count: int = 0
    newly_visible_cells_count: int = 0
    true_los_cells_count: int = 0
    true_los_candidates_count: int = 0
    true_los_blocked_count: int = 0
    los_cells_count: int = 0
    graph_cells_count: int = 0
    seed_cells_count: int = 0
    hybrid_cells_count: int = 0
    expanded_cells_count: int = 0
    viewport_radius_cells: Optional[int] = 25
    viewport_box: Optional[Dict[str, int]] = None
    vision_profile: Optional[Dict[str, Any]] = None
    fov_anchor: Optional[Dict[str, Any]] = None
    fov_mode: str = "state_visible_cells"
    fov_fallback_used: bool = False
    fog_alpha: int = 252
    explored_alpha: int = 145
    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RuntimeVisibilityMapService:
    """Renders channel-specific FOV/Fog-of-War maps."""

    def __init__(self, bundle_dir: str | Path, campaign_id: str) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.campaign_id = str(campaign_id)

    def render_for_channel(
        self,
        channel_id: str,
        *,
        output_file: str | Path | None = None,
        fog_alpha: int = 252,
        explored_alpha: int = 145,
        reveal_padding: int = 0,
        draw_cell_outline: bool = False,
        mark_current_cell: bool = True,
        vision_name: str = "torch",
        bright_radius_cells: int | None = None,
        dim_radius_cells: int | None = None,
        darkvision_radius_cells: int | None = None,
        map_mode: str = "local",
        viewport_radius_cells: int = 25,
        crop_padding_pixels: int = 0,
        fov_mode: str = "state_visible_cells",
    ) -> RuntimeVisibilityMapResult:
        state_file = self._state_file(channel_id)
        state = VisibilityStateStore(state_file).load()
        if not state:
            return RuntimeVisibilityMapResult(
                ok=False,
                message="Nincs mentett visibility state ehhez a csatornához. Előbb nézz körül vagy lépj egyet.",
                map_mode=map_mode,
            )

        level = self._current_level(state)
        visible_cells = self._visible_cells(state)
        current_cell = self._current_cell(state) if mark_current_cell else None
        if current_cell:
            visible_cells.add(current_cell)

        if not visible_cells:
            return RuntimeVisibilityMapResult(
                ok=False,
                message="Nincs látható cella a térkép rendereléséhez.",
                level=level,
                map_mode=map_mode,
                fog_alpha=fog_alpha,
            )

        source_map, cell_size = self._source_map_for_level(level)
        if not source_map:
            return RuntimeVisibilityMapResult(
                ok=False,
                message=f"Nem található player map a(z) {level}. szinthez.",
                level=level,
                map_mode=map_mode,
                fog_alpha=fog_alpha,
            )

        previous_explored = self._explored_cells(state)
        explored_cells = set(previous_explored) | set(visible_cells)
        newly_visible = set(visible_cells) - previous_explored

        warning = None
        try:
            if FogOfWarPolicy is not None:
                FogOfWarPolicy.apply_visible_cells(state, visible_cells)
                if current_cell is not None:
                    FogOfWarPolicy.mark_current_cell_visited(state)
            else:
                state.visible_cells = sorted(visible_cells)
                state.explored_cells = sorted(explored_cells)
            VisibilityStateStore(state_file).save(state)
        except Exception as exc:  # pragma: no cover - should not block rendering
            warning = f"FOW state save failed: {exc}"

        mode = "full" if str(map_mode or "").lower() in {"full", "level"} else "local"
        output = Path(output_file) if output_file else self._default_output_file(channel_id, level, mode)
        full_temp = output if mode == "full" else output.with_name(output.stem + "_full_tmp" + output.suffix)

        try:
            rendered = self._render_fow(
                source_map=source_map,
                visible_cells=visible_cells,
                explored_cells=explored_cells,
                output_file=full_temp,
                cell_size=cell_size,
                fog_alpha=fog_alpha,
                explored_alpha=explored_alpha,
                reveal_padding=reveal_padding,
                draw_cell_outline=draw_cell_outline,
                current_cell=current_cell,
            )
            viewport_box = None
            if mode == "local":
                viewport_box = self._crop_viewport(
                    rendered_full_map=Path(rendered),
                    output=output,
                    cells=visible_cells,
                    cell_size=cell_size,
                    current_cell=current_cell,
                    viewport_radius_cells=viewport_radius_cells,
                    crop_padding_pixels=crop_padding_pixels,
                )
                try:
                    if Path(rendered) != output and Path(rendered).exists():
                        Path(rendered).unlink()
                except Exception:
                    pass
                rendered = str(output)
        except Exception as exc:
            return RuntimeVisibilityMapResult(
                ok=False,
                message=f"Nem sikerült a térkép renderelése: {exc}",
                level=level,
                map_mode=mode,
                source_map=str(source_map),
                warning=str(exc),
            )

        return RuntimeVisibilityMapResult(
            ok=True,
            message=f"Térkép elkészült: {rendered}",
            output_file=str(rendered),
            source_map=str(source_map),
            level=level,
            map_mode=mode,
            visible_cells_count=len(visible_cells),
            explored_cells_count=len(explored_cells),
            newly_visible_cells_count=len(newly_visible),
            expanded_cells_count=len(visible_cells),
            viewport_radius_cells=viewport_radius_cells if mode == "local" else None,
            viewport_box=viewport_box,
            fov_mode=str(fov_mode or "state_visible_cells"),
            fog_alpha=fog_alpha,
            explored_alpha=explored_alpha,
            warning=warning,
        )

    def _render_fow(
        self,
        *,
        source_map: Path,
        visible_cells: Iterable[Cell],
        explored_cells: Iterable[Cell],
        output_file: Path,
        cell_size: int,
        fog_alpha: int,
        explored_alpha: int,
        reveal_padding: int,
        draw_cell_outline: bool,
        current_cell: Optional[Cell],
    ) -> str:
        renderer = FogCellRenderer()
        try:
            return renderer.render(
                source_map,
                visible_cells,
                output_file,
                explored_cells=explored_cells,
                cell_size=cell_size,
                fog_alpha=fog_alpha,
                explored_alpha=explored_alpha,
                reveal_padding=reveal_padding,
                draw_cell_outline=draw_cell_outline,
                current_cell=current_cell,
            )
        except TypeError:
            # Compatibility with older FogCellRenderer signature.
            return renderer.render(source_map, visible_cells, output_file, cell_size=cell_size, fog_alpha=fog_alpha)

    def _crop_viewport(
        self,
        *,
        rendered_full_map: Path,
        output: Path,
        cells: Set[Cell],
        cell_size: int,
        current_cell: Optional[Cell],
        viewport_radius_cells: int,
        crop_padding_pixels: int = 0,
    ) -> Dict[str, int]:
        from PIL import Image

        img = Image.open(rendered_full_map).convert("RGBA")
        radius = max(1, int(viewport_radius_cells or 25))
        center = current_cell or self._centroid_cell(cells) or (0, 0)
        cr, cc = center
        cell = max(1, int(cell_size or 14))
        pad = max(0, int(crop_padding_pixels or 0))
        x0 = max(0, (cc - radius) * cell - pad)
        y0 = max(0, (cr - radius) * cell - pad)
        x1 = min(img.size[0], (cc + radius + 1) * cell + pad)
        y1 = min(img.size[1], (cr + radius + 1) * cell + pad)
        crop = img.crop((int(x0), int(y0), int(x1), int(y1)))
        output.parent.mkdir(parents=True, exist_ok=True)
        crop.save(output)
        return {"x0": int(x0), "y0": int(y0), "x1": int(x1), "y1": int(y1), "width": int(x1 - x0), "height": int(y1 - y0)}

    @staticmethod
    def _centroid_cell(cells: Set[Cell]) -> Optional[Cell]:
        if not cells:
            return None
        return (
            round(sum(r for r, _ in cells) / len(cells)),
            round(sum(c for _, c in cells) / len(cells)),
        )

    def _state_file(self, channel_id: str) -> Path:
        safe = str(channel_id).replace("/", "_").replace("\\", "_")
        return self.bundle_dir / f"visibility_runtime_state_{safe}.json"

    def _default_output_file(self, channel_id: str, level: int, mode: str) -> Path:
        safe = str(channel_id).replace("/", "_").replace("\\", "_")
        suffix = "full" if mode == "full" else "view"
        return self.bundle_dir / f"runtime_visibility_map_{safe}_L{int(level):02d}_{suffix}.png"

    def _current_level(self, state: Any) -> int:
        current = getattr(state, "current", None)
        if current and getattr(current, "level", None):
            return int(current.level)
        return 1

    def _current_cell(self, state: Any) -> Optional[Cell]:
        current = getattr(state, "current", None)
        raw = getattr(current, "cell", None) if current else None
        return self._cell_from_any(raw)

    def _visible_cells(self, state: Any) -> Set[Cell]:
        return self._cell_set(getattr(state, "visible_cells", []) or [])

    def _explored_cells(self, state: Any) -> Set[Cell]:
        explored = self._cell_set(getattr(state, "explored_cells", []) or [])
        return explored or set(self._visible_cells(state))

    @staticmethod
    def _cell_from_any(value: Any) -> Optional[Cell]:
        if value is None:
            return None
        try:
            r, c = value
            return int(r), int(c)
        except Exception:
            return None

    @classmethod
    def _cell_set(cls, values: Any) -> Set[Cell]:
        out: Set[Cell] = set()
        for item in values or []:
            cell = cls._cell_from_any(item)
            if cell is not None:
                out.add(cell)
        return out

    def _source_map_for_level(self, level: int) -> tuple[Optional[Path], int]:
        cell_size = 14
        for manifest_name in ("fog_manifest.json", "map_geometry.json"):
            data = self._read_json(manifest_name)
            for entry in data.get("levels", []) or []:
                try:
                    entry_level = int(entry.get("level") or entry.get("level_number") or 0)
                except Exception:
                    entry_level = 0
                if entry_level != int(level):
                    continue
                cell_size = int(entry.get("cell_size") or cell_size or 14)
                for key in (
                    "players_map_image",
                    "players_map",
                    "player_map",
                    "map_players",
                    "players_map_file",
                ):
                    if entry.get(key):
                        p = self._resolve_path(entry[key])
                        if p.exists():
                            return p, cell_size

        candidates: list[tuple[int, Path]] = []
        for p in self.bundle_dir.rglob("*.png"):
            name = p.name.lower()
            score = 0
            if f"l{int(level):02d}" in name or f"level_{int(level):02d}" in str(p).lower():
                score += 10
            if "player" in name or "players" in name:
                score += 5
            if "map" in name:
                score += 2
            if score:
                candidates.append((score, p))
        if candidates:
            candidates.sort(key=lambda x: (-x[0], str(x[1])))
            return candidates[0][1], cell_size
        return None, cell_size

    def _resolve_path(self, value: str | Path) -> Path:
        p = Path(value)
        if p.is_absolute():
            return p
        direct = Path(value)
        if direct.exists():
            return direct
        bundle_relative = self.bundle_dir / p
        if bundle_relative.exists():
            return bundle_relative
        return bundle_relative

    def _read_json(self, name: str) -> Dict[str, Any]:
        p = self.bundle_dir / name
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
