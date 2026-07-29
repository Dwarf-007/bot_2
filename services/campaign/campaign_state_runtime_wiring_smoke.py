"""
SERVICES/CAMPAIGN/CAMPAIGN_STATE_RUNTIME_WIRING_SMOKE.PY
Runtime wiring smoke for G2 Campaign State foundation.

G2.5 purpose:
- Verify that G2.1-G2.4 compose in a runtime-like workflow.
- Exercise approved transition application into CampaignStateStore.
- Exercise read-only query context after state changes.
- Verify optional repository bridge compatibility without requiring a database.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No TurnOutput dependency.
- State mutation is limited to approved G2 CampaignStateStore updates.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

from services.campaign.campaign_state_models import CampaignState, CampaignSnapshot
from services.campaign.campaign_state_query_service import CampaignStateQueryService
from services.campaign.campaign_state_store import CampaignStateStore
from services.campaign.campaign_transition_application_service import CampaignTransitionApplicationService
from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionApprovalStatus,
    CampaignStateTransitionProposal,
    CampaignStateTransitionRisk,
    CampaignStateTransitionType,
)
from services.compendium.campaign_transition_approval_policy import CampaignTransitionApprovalPolicy


CANONICAL_G2_FILES: tuple[str, ...] = (
    "services/campaign/campaign_state_models.py",
    "services/campaign/campaign_state_store.py",
    "services/campaign/campaign_transition_application_service.py",
    "services/campaign/campaign_state_query_service.py",
    "services/campaign/campaign_state_runtime_wiring_smoke.py",
)

FORBIDDEN_RUNTIME_MARKERS: tuple[str, ...] = (
    "dispatch_commands",
    "AvraeDispatcher(",
    "AvraeClient(",
    ".is_available()",
    "message.channel.send",
    "TurnOutput",
)


@dataclass(frozen=True)
class CampaignStateRuntimeComponents:
    state_store: CampaignStateStore
    approval_policy: CampaignTransitionApprovalPolicy
    application_service: CampaignTransitionApplicationService
    query_service: CampaignStateQueryService


@dataclass(frozen=True)
class CampaignStateRuntimeSmokeCheck:
    name: str
    ok: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignStateRuntimeSmokeResult:
    ok: bool
    checks: List[CampaignStateRuntimeSmokeCheck] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
            "stats": dict(self.stats),
        }

    def summary_text(self) -> str:
        passed = sum(1 for check in self.checks if check.ok)
        lines = [f"CampaignState G2 runtime wiring smoke: {passed}/{len(self.checks)} passed"]
        for check in self.checks:
            prefix = "OK" if check.ok else "FAIL"
            lines.append(f"- {prefix} {check.name}: {check.message}".rstrip())
        return "
".join(lines)


class CampaignStateRuntimeWiringBuilder:
    """Composition helper for G2 campaign state services."""

    def build(
        self,
        campaign_progress_repository: Any | None = None,
        location_repository: Any | None = None,
        campaign_repository: Any | None = None,
        room_alias_repository: Any | None = None,
    ) -> CampaignStateRuntimeComponents:
        state_store = CampaignStateStore()
        approval_policy = CampaignTransitionApprovalPolicy()
        application_service = CampaignTransitionApplicationService(
            state_store=state_store,
            approval_policy=approval_policy,
            campaign_progress_repository=campaign_progress_repository,
            location_repository=location_repository,
            campaign_repository=campaign_repository,
            room_alias_repository=room_alias_repository,
        )
        query_service = CampaignStateQueryService(
            state_store=state_store,
            campaign_repository=campaign_repository,
            campaign_progress_repository=campaign_progress_repository,
            location_repository=location_repository,
            room_alias_repository=room_alias_repository,
        )
        return CampaignStateRuntimeComponents(
            state_store=state_store,
            approval_policy=approval_policy,
            application_service=application_service,
            query_service=query_service,
        )


class CampaignStateRuntimeWiringSmoke:
    """Runs runtime-like smoke checks for G2 state services."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)

    def run(self) -> CampaignStateRuntimeSmokeResult:
        fake_progress = FakeCampaignProgressRepository()
        fake_locations = FakeLocationRepository()
        fake_aliases = FakeRoomAliasRepository()
        components = CampaignStateRuntimeWiringBuilder().build(
            campaign_progress_repository=fake_progress,
            location_repository=fake_locations,
            room_alias_repository=fake_aliases,
        )
        return self._run_components(components, fake_progress=fake_progress, fake_locations=fake_locations, fake_aliases=fake_aliases)

    def _run_components(
        self,
        components: CampaignStateRuntimeComponents,
        fake_progress: Any | None = None,
        fake_locations: Any | None = None,
        fake_aliases: Any | None = None,
    ) -> CampaignStateRuntimeSmokeResult:
        checks: List[CampaignStateRuntimeSmokeCheck] = []

        campaign_id = "sandbox-g2"
        scene_id = "old-road"
        initial = CampaignState(campaign_id=campaign_id, title="G2 Sandbox")
        components.state_store.save_campaign(initial)
        checks.append(CampaignStateRuntimeSmokeCheck(
            name="initial_state_saved",
            ok=components.state_store.get_campaign(campaign_id) is initial,
            message="Initial campaign state saved in CampaignStateStore.",
        ))

        approved_proposals = [
            CampaignStateTransitionProposal(
                proposal_id="sandbox-g2:old-road:location-unlocked:old-watchtower",
                campaign_id=campaign_id,
                scene_id=scene_id,
                transition_type=CampaignStateTransitionType.LOCATION_UNLOCKED,
                title="Old Watchtower unlocked",
                summary="The party learned about the old watchtower.",
                risk=CampaignStateTransitionRisk.LOW,
                approval_required=False,
                approval_status=CampaignStateTransitionApprovalStatus.APPROVED,
                state_patch_preview={"location_id": "old-watchtower", "title": "Old Watchtower"},
            ),
            CampaignStateTransitionProposal(
                proposal_id="sandbox-g2:old-road:quest-clue-discovered:smoke-clue",
                campaign_id=campaign_id,
                scene_id=scene_id,
                transition_type=CampaignStateTransitionType.QUEST_CLUE_DISCOVERED,
                title="Smoke clue discovered",
                summary="Smoke near the old tower may connect to missing caravans.",
                player_visible_summary="A clue points toward smoke near the old tower.",
                risk=CampaignStateTransitionRisk.LOW,
                approval_required=False,
                approval_status=CampaignStateTransitionApprovalStatus.APPROVED,
            ),
            CampaignStateTransitionProposal(
                proposal_id="sandbox-g2:old-road:branch-available:follow-trail",
                campaign_id=campaign_id,
                scene_id=scene_id,
                transition_type=CampaignStateTransitionType.BRANCH_AVAILABLE,
                title="Follow the trail",
                summary="The party may follow the trail toward the tower.",
                risk=CampaignStateTransitionRisk.MEDIUM,
                approval_required=True,
                approval_status=CampaignStateTransitionApprovalStatus.APPROVED,
                recommended_next_steps=["Ask whether the party follows the trail now."],
            ),
            CampaignStateTransitionProposal(
                proposal_id="sandbox-g2:old-road:scene-entered:old-road",
                campaign_id=campaign_id,
                scene_id=scene_id,
                transition_type=CampaignStateTransitionType.SCENE_ENTERED,
                title="Old Road entered",
                summary="The party entered the old road scene.",
                risk=CampaignStateTransitionRisk.LOW,
                approval_required=False,
                approval_status=CampaignStateTransitionApprovalStatus.APPROVED,
                state_patch_preview={"scene_id": scene_id, "room_id": "old-road-room"},
            ),
        ]
        apply_result = components.application_service.apply_proposals(
            campaign_id=campaign_id,
            scene_id=scene_id,
            proposals=approved_proposals,
            channel_id="channel-1",
        )
        checks.append(CampaignStateRuntimeSmokeCheck(
            name="approved_proposals_applied",
            ok=apply_result.applied_count == 4,
            message="Approved proposals were applied to campaign state.",
            details={"summary": apply_result.summary, "records": [asdict(record) for record in apply_result.records]},
        ))

        state = components.state_store.get_campaign(campaign_id)
        checks.append(CampaignStateRuntimeSmokeCheck(
            name="state_contains_location_clue_and_quest_candidate",
            ok=(
                state is not None
                and "old-watchtower" in state.locations
                and "old-watchtower" in state.knowledge.known_locations
                and "A clue points toward smoke near the old tower." in state.knowledge.known_clues
                and any(quest.title == "Follow the trail" for quest in state.quests.values())
            ),
            message="Campaign state contains applied location, clue, and quest candidate.",
            details={"known_locations": list(state.knowledge.known_locations) if state else [], "known_clues": list(state.knowledge.known_clues) if state else []},
        ))

        summary = components.query_service.summarize(campaign_id)
        runtime_context = components.query_service.get_runtime_context(campaign_id, channel_id="channel-1")
        checks.append(CampaignStateRuntimeSmokeCheck(
            name="query_service_reads_updated_context",
            ok=(
                "old-watchtower" in summary.known_locations
                and "old-road-room" in summary.visited_locations
                and runtime_context.current_scene_id == scene_id
                and runtime_context.current_room_id == "old-road-room"
                and runtime_context.repository_context.get("open_objectives") == ["objective-1"]
            ),
            message="CampaignStateQueryService reads updated runtime context.",
            details={"summary": asdict(summary), "runtime_context": _runtime_context_debug(runtime_context)},
        ))

        snapshot = CampaignSnapshot(snapshot_id="snap-1", campaign_id=campaign_id, state=state)
        components.state_store.create_snapshot(snapshot)
        restored = components.state_store.restore_snapshot("snap-1")
        checks.append(CampaignStateRuntimeSmokeCheck(
            name="snapshot_roundtrip",
            ok=restored is state,
            message="CampaignStateStore snapshot restore works.",
        ))

        blocked = CampaignStateTransitionProposal(
            proposal_id="sandbox-g2:branch:branch-selected:forced",
            campaign_id=campaign_id,
            scene_id="branch",
            transition_type=CampaignStateTransitionType.BRANCH_SELECTED,
            title="Forced branch",
            summary="Never-auto branch selection.",
            risk=CampaignStateTransitionRisk.HIGH,
            approval_required=True,
            approval_status=CampaignStateTransitionApprovalStatus.APPROVED,
        )
        blocked_result = components.application_service.apply_proposals(campaign_id, "branch", [blocked])
        checks.append(CampaignStateRuntimeSmokeCheck(
            name="never_auto_is_blocked",
            ok=blocked_result.applied_count == 0 and blocked_result.blocked_count == 1,
            message="Never-auto transition was blocked by application service.",
            details={"records": [asdict(record) for record in blocked_result.records]},
        ))

        alias_room = components.query_service.resolve_room_alias(campaign_id, "old tower")
        checks.append(CampaignStateRuntimeSmokeCheck(
            name="room_alias_bridge",
            ok=alias_room == "old-watchtower",
            message="Room alias repository bridge resolved a room id.",
            details={"alias_room": alias_room},
        ))

        missing_files, violations = self._scan_no_runtime_coupling(CANONICAL_G2_FILES, FORBIDDEN_RUNTIME_MARKERS)
        checks.append(CampaignStateRuntimeSmokeCheck(
            name="canonical_g2_files_present",
            ok=not missing_files,
            message="All canonical G2 files are present." if not missing_files else "Some canonical G2 files are missing.",
            details={"missing_files": missing_files},
        ))
        checks.append(CampaignStateRuntimeSmokeCheck(
            name="no_runtime_coupling",
            ok=not violations,
            message="No Discord/Avrae/TurnOutput runtime coupling markers found in G2 state path." if not violations else "Forbidden runtime markers found.",
            details={"violations": violations},
        ))

        return CampaignStateRuntimeSmokeResult(
            ok=all(check.ok for check in checks),
            checks=checks,
            stats={
                "campaign_id": campaign_id,
                "checks": len(checks),
                "applied_count": apply_result.applied_count,
                "known_locations": len(summary.known_locations),
                "known_clues": len(summary.known_clues),
            },
        )

    def _scan_no_runtime_coupling(self, files: Iterable[str], markers: Iterable[str]) -> tuple[List[str], List[Dict[str, str]]]:
        missing: List[str] = []
        violations: List[Dict[str, str]] = []
        for rel_path in files:
            path = self.project_root / rel_path
            if not path.exists():
                missing.append(rel_path)
                continue
            text = path.read_text(encoding="utf-8")
            for marker in markers:
                if marker in text:
                    violations.append({"file": rel_path, "marker": marker})
        return missing, violations


class FakeCampaignProgressRepository:
    def __init__(self) -> None:
        self.progress_calls: List[Dict[str, Any]] = []
        self.objective_calls: List[Dict[str, Any]] = []

    def set_channel_progress(self, **kwargs) -> None:
        self.progress_calls.append(kwargs)

    def get_channel_progress(self, channel_id: str):
        class Progress:
            current_scene_id = "old-road"
            current_room_id = "old-road-room"
            milestone = "scene_entered"
        return Progress()

    def add_objective(self, **kwargs) -> int:
        self.objective_calls.append(kwargs)
        return 1

    def list_objectives(self, channel_id: str):
        return ["objective-1"]


class FakeLocationRepository:
    def get_room(self, room_id: str):
        return {"room_id": room_id, "title": room_id.replace("-", " ").title()}

    def list_rooms(self, campaign_id: str):
        return [{"room_id": "old-road-room"}, {"room_id": "old-watchtower"}]


class FakeRoomAliasRepository:
    def search_aliases(self, campaign_id: str, query: str, limit: int = 1):
        class Record:
            room_id = "old-watchtower"
        return [Record()]


def _runtime_context_debug(context) -> Dict[str, Any]:
    return {
        "campaign_id": context.campaign_id,
        "channel_id": context.channel_id,
        "current_scene_id": context.current_scene_id,
        "current_room_id": context.current_room_id,
        "milestone": context.milestone,
        "repository_context_keys": sorted(context.repository_context.keys()),
    }
