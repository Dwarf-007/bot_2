from __future__ import annotations
from pathlib import Path
from typing import Optional
from models.movement_models import MovementState

class MovementMapService:
    def __init__(self, bundle_dir: str | Path) -> None:
        self.bundle_dir = Path(bundle_dir)

    def render_map(self, state: MovementState, level: Optional[int] = None, show_adjacent: bool = True, output_file: Optional[str | Path] = None) -> Optional[str]:
        try:
            from services.dungeons.fog_of_war_renderer import FogOfWarRenderer
        except Exception:
            return None
        level = level or self._level_from_room_id(state.current_room_id)
        if level is None:
            return None
        out = Path(output_file) if output_file else self.bundle_dir / f'fog_current_L{level:02d}.png'
        return FogOfWarRenderer().render(
            self.bundle_dir / 'map_geometry.json',
            level,
            state.visited_rooms,
            out,
            current_room_id=state.current_room_id,
            show_adjacent=show_adjacent,
            graph_file=self.bundle_dir / 'dungeon_graph.json',
        )

    @staticmethod
    def _level_from_room_id(room_id: str) -> Optional[int]:
        import re
        m = re.search(r':L(\d+):', room_id or '')
        return int(m.group(1)) if m else None
