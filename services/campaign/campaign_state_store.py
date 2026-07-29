
from __future__ import annotations
from dataclasses import asdict
from typing import Dict
from services.campaign.campaign_state_models import CampaignState, CampaignSnapshot

class CampaignStateStore:
    def __init__(self)->None:
        self._campaigns: Dict[str, CampaignState] = {}
        self._snapshots: Dict[str, CampaignSnapshot] = {}

    def save_campaign(self, state: CampaignState) -> None:
        self._campaigns[state.campaign_id] = state

    def load_campaign(self, campaign_id:str) -> CampaignState | None:
        return self._campaigns.get(campaign_id)

    def get_campaign(self, campaign_id:str) -> CampaignState | None:
        return self.load_campaign(campaign_id)

    def create_snapshot(self, snapshot: CampaignSnapshot) -> None:
        self._snapshots[snapshot.snapshot_id] = snapshot

    def get_snapshot(self, snapshot_id:str) -> CampaignSnapshot | None:
        return self._snapshots.get(snapshot_id)

    def restore_snapshot(self, snapshot_id:str) -> CampaignState | None:
        snap=self._snapshots.get(snapshot_id)
        if snap:
            self._campaigns[snap.campaign_id]=snap.state
            return snap.state
        return None
