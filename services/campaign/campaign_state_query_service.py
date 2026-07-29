"""
SERVICES/CAMPAIGN/CAMPAIGN_STATE_QUERY_SERVICE.PY
Read/query facade over the G2 campaign state layer.

G2.4 purpose:
- Provide runtime-friendly read access to CampaignStateStore.
- Summarize current campaign state for sandbox, donjon, and campaign runtime.
- Optionally bridge to existing repositories such as CampaignProgressRepository,
  LocationRepository, CampaignRepository, and RoomAliasRepository.

Boundary:
- Read-only service.
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No campaign state mutation.
- No TurnOutput dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from services.campaign.campaign_state_models import (
    CampaignState,
    LocationState,
    NpcState,
    FactionState,
    QuestState,
)
from services.campaign.campaign_state_store import CampaignStateStore


@dataclass(frozen=True)
class CampaignStateSummary:
    campaign_id: str
    title: str = ""
    theme: str = ""
    tone: str = ""
    active_location_id: str = ""
    known_locations: List[str] = field(default_factory=list)
    visited_locations: List[str] = field(default_factory=list)
    known_npcs: List[str] = field(default_factory=list)
    active_quests: List[str] = field(default_factory=list)
    known_clues: List[str] = field(default_factory=list)
    world_truth_count: int = 0
    hidden_truth_count: int = 0


@dataclass(frozen=True)
class CampaignRuntimeContext:
    campaign_id: str
    channel_id: str = ""
    current_scene_id: Optional[str] = None
    current_room_id: Optional[str] = None
    milestone: str = ""
    summary: Optional[CampaignStateSummary] = None
    active_location: Optional[LocationState] = None
    active_quests: List[QuestState] = field(default_factory=list)
    known_npcs: List[NpcState] = field(default_factory=list)
    factions: List[FactionState] = field(default_factory=list)
    repository_context: Dict[str, Any] = field(default_factory=dict)


class CampaignStateQueryService:
    """Read-only query facade for campaign state and optional repository context."""

    def __init__(
        self,
        state_store: CampaignStateStore,
        campaign_repository: Any | None = None,
        campaign_progress_repository: Any | None = None,
        location_repository: Any | None = None,
        room_alias_repository: Any | None = None,
    ) -> None:
        self.state_store = state_store
        self.campaign_repository = campaign_repository
        self.campaign_progress_repository = campaign_progress_repository
        self.location_repository = location_repository
        self.room_alias_repository = room_alias_repository

    def get_state(self, campaign_id: str) -> Optional[CampaignState]:
        return self.state_store.get_campaign(campaign_id)

    def summarize(self, campaign_id: str) -> CampaignStateSummary:
        state = self.state_store.get_campaign(campaign_id)
        if state is None:
            return CampaignStateSummary(campaign_id=campaign_id)

        known_locations = list(state.knowledge.known_locations)
        visited_locations = [loc.location_id for loc in state.locations.values() if loc.visited]
        known_npcs = list(state.knowledge.known_npcs) or list(state.npcs.keys())
        active_quests = [quest.quest_id for quest in state.quests.values() if str(quest.status).lower().endswith('active') or str(quest.status) == 'QuestStatus.ACTIVE']
        hidden_truth_count = sum(1 for truth in state.world_truths if not truth.revealed)

        return CampaignStateSummary(
            campaign_id=state.campaign_id,
            title=state.title,
            theme=state.theme,
            tone=state.tone,
            active_location_id=state.active_location_id,
            known_locations=known_locations,
            visited_locations=visited_locations,
            known_npcs=known_npcs,
            active_quests=active_quests,
            known_clues=list(state.knowledge.known_clues),
            world_truth_count=len(state.world_truths),
            hidden_truth_count=hidden_truth_count,
        )

    def get_runtime_context(self, campaign_id: str, channel_id: str = "") -> CampaignRuntimeContext:
        state = self.state_store.get_campaign(campaign_id)
        summary = self.summarize(campaign_id)
        progress = self._get_channel_progress(channel_id) if channel_id else None
        current_scene_id = getattr(progress, 'current_scene_id', None) if progress else None
        current_room_id = getattr(progress, 'current_room_id', None) if progress else None
        milestone = getattr(progress, 'milestone', '') if progress else ''

        active_location_id = current_room_id or summary.active_location_id
        active_location = state.locations.get(active_location_id) if state and active_location_id else None
        active_quests = self.list_active_quests(campaign_id)
        known_npcs = self.list_known_npcs(campaign_id)
        factions = list(state.factions.values()) if state else []

        return CampaignRuntimeContext(
            campaign_id=campaign_id,
            channel_id=channel_id,
            current_scene_id=current_scene_id,
            current_room_id=current_room_id,
            milestone=milestone,
            summary=summary,
            active_location=active_location,
            active_quests=active_quests,
            known_npcs=known_npcs,
            factions=factions,
            repository_context=self._repository_context(campaign_id, channel_id, current_room_id),
        )

    def list_known_locations(self, campaign_id: str) -> List[LocationState]:
        state = self.state_store.get_campaign(campaign_id)
        if state is None:
            return []
        ids = set(state.knowledge.known_locations)
        return [loc for loc in state.locations.values() if loc.location_id in ids or loc.discovered]

    def list_visited_locations(self, campaign_id: str) -> List[LocationState]:
        state = self.state_store.get_campaign(campaign_id)
        if state is None:
            return []
        return [loc for loc in state.locations.values() if loc.visited]

    def list_active_quests(self, campaign_id: str) -> List[QuestState]:
        state = self.state_store.get_campaign(campaign_id)
        if state is None:
            return []
        return [quest for quest in state.quests.values() if str(quest.status).lower().endswith('active') or str(quest.status) == 'QuestStatus.ACTIVE']

    def list_known_npcs(self, campaign_id: str) -> List[NpcState]:
        state = self.state_store.get_campaign(campaign_id)
        if state is None:
            return []
        ids = set(state.knowledge.known_npcs)
        if not ids:
            return list(state.npcs.values())
        return [npc for npc in state.npcs.values() if npc.npc_id in ids]

    def list_known_clues(self, campaign_id: str) -> List[str]:
        state = self.state_store.get_campaign(campaign_id)
        return list(state.knowledge.known_clues) if state else []

    def resolve_room_alias(self, campaign_id: str, query: str) -> Optional[str]:
        if self.room_alias_repository is None:
            return None
        if hasattr(self.room_alias_repository, 'find_best_alias'):
            record = self.room_alias_repository.find_best_alias(campaign_id, query)
            return getattr(record, 'room_id', None) if record else None
        if hasattr(self.room_alias_repository, 'search_aliases'):
            records = self.room_alias_repository.search_aliases(campaign_id, query, limit=1)
            if records:
                return getattr(records[0], 'room_id', None)
        return None

    def _get_channel_progress(self, channel_id: str):
        if self.campaign_progress_repository is not None and hasattr(self.campaign_progress_repository, 'get_channel_progress'):
            return self.campaign_progress_repository.get_channel_progress(channel_id)
        return None

    def _repository_context(self, campaign_id: str, channel_id: str, current_room_id: Optional[str]) -> Dict[str, Any]:
        context: Dict[str, Any] = {}
        if self.campaign_repository is not None and hasattr(self.campaign_repository, 'get_campaign'):
            record = self.campaign_repository.get_campaign(campaign_id)
            if record is not None:
                context['campaign_record'] = record
        if self.location_repository is not None:
            if current_room_id and hasattr(self.location_repository, 'get_room'):
                context['current_room_record'] = self.location_repository.get_room(current_room_id)
            if hasattr(self.location_repository, 'list_rooms'):
                context['room_count'] = len(self.location_repository.list_rooms(campaign_id))
        if self.campaign_progress_repository is not None and channel_id and hasattr(self.campaign_progress_repository, 'list_objectives'):
            context['open_objectives'] = self.campaign_progress_repository.list_objectives(channel_id)
        return context
