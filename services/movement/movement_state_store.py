from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from models.movement_models import MovementState

class MovementStateStore:
    def __init__(self, state_file: str | Path) -> None:
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Optional[MovementState]:
        if not self.state_file.exists():
            return None
        return MovementState.from_dict(json.loads(self.state_file.read_text(encoding='utf-8')))

    def save(self, state: MovementState) -> None:
        self.state_file.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

    def init(self, campaign_id: str, start_room_id: str, overwrite: bool = False) -> MovementState:
        if self.state_file.exists() and not overwrite:
            loaded = self.load()
            if loaded:
                return loaded
        state = MovementState(campaign_id=campaign_id, current_room_id=start_room_id, visited_rooms=[start_room_id], path_history=[])
        self.save(state)
        return state
