from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from models.corridor_visibility_models import VisibilityState

class VisibilityStateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
    def load(self) -> Optional[VisibilityState]:
        if not self.path.exists(): return None
        return VisibilityState.from_dict(json.loads(self.path.read_text(encoding='utf-8')))
    def save(self, state: VisibilityState) -> None:
        self.path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
