from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from models.secret_discovery_models import SecretDiscoveryState


class SecretDiscoveryStateStore:
    def __init__(self, state_file: str | Path) -> None:
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Optional[SecretDiscoveryState]:
        if not self.state_file.exists():
            return None
        return SecretDiscoveryState.from_dict(json.loads(self.state_file.read_text(encoding='utf-8')))

    def save(self, state: SecretDiscoveryState) -> None:
        self.state_file.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

    def init(self, campaign_id: str, scope_id: str = "party", overwrite: bool = False) -> SecretDiscoveryState:
        if self.state_file.exists() and not overwrite:
            loaded = self.load()
            if loaded:
                return loaded
        state = SecretDiscoveryState(campaign_id=campaign_id, scope_id=scope_id)
        self.save(state)
        return state
