"""
SERVICES/CAMPAIGN/CAMPAIGN_STATE_AGGREGATE_GATE.PY
Aggregate gate for the G2 Campaign State foundation.

G2.6 purpose:
- Close the G2.1-G2.5 Campaign State MVP slice.
- Run/adapt the G2.5 runtime wiring smoke.
- Verify model/store/application/query contracts together.
- Verify repository bridge compatibility.
- Verify no Discord/Avrae/TurnOutput coupling in the G2 state layer.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No TurnOutput dependency.
- State mutation is limited to approved proposal application through G2.3.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

from services.campaign.campaign_state_models import CampaignState, LocationState, QuestStatus
from services.campaign.campaign_state_query_service import CampaignStateQueryService
from services.campaign.campaign_state_runtime_wiring_smoke import CampaignStateRuntimeWiringSmoke
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
    "services/campaign/campaign_state_aggregate_gate.py",
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
class CampaignStateAggregateCheck:
    name: str
    ok: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignStateAggregateResult:
    ok: bool
    checks: List[CampaignStateAggregateCheck] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
            "stats": dict(self.stats),
        }

    def summary_text(self) -> str:
        passed = sum(1 for check in self.checks if check.ok)
        lines = [f"CampaignState G2 aggregate gate: {passed}/{len(self.checks)} passed"]
        for check in self.checks:
            prefix = "OK" if check.ok else "FAIL"
            lines.append(f"- {prefix} {check.name}: {check.message}".rstrip())
        return "
".join(lines)


class CampaignStateAggregateGate:
    """Runs the G2 Campaign State aggregate gate."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)

    def run(self) -> CampaignStateAggregateResult:
        checks: List[CampaignStateAggregateCheck] = []

        runtime_smoke = CampaignStateRuntimeWiringSmoke(project_root=self.project_root).run()
        checks.append(CampaignStateAggregateCheck(
            name="g2_05_runtime_wiring_smoke",
            ok=runtime_smoke.ok,
            message="G2.5 runtime wiring smoke passed." if runtime_smoke.ok else "G2.5 runtime wiring smoke failed.",
            details={"summary": runtime_smoke.summary_text(), "stats": dict(runtime_smoke.stats)},
        ))

        checks.append(self._check_model_contract())
        checks.append(self._check_store_contract())
        checks.append(self._check_application_contract())
        checks.append(self._check_query_contract())

        missing_files, violations = self._scan_no_runtime_coupling(CANONICAL_G2_FILES, FORBIDDEN_RUNTIME_MARKERS)
        checks.append(CampaignStateAggregateCheck(
            name="canonical_g2_files_present",
            ok=not missing_files,
            message="All canonical G2 files are present." if not missing_files else "Some canonical G2 files are missing.",
            details={"missing_files": missing_files},
        ))
        checks.append(CampaignStateAggregateCheck(
            name="no_runtime_coupling",
            ok=not violations,
            message="No Discord/Avrae/TurnOutput runtime coupling markers found in G2 state path." if not violations else "Forbidden runtime markers found.",
            details={"violations": violations},
        ))

        return CampaignStateAggregateResult(
            ok=all(check.ok for check in checks),
            checks=checks,
            stats={
                "checks": len(checks),
                "g2_05_ok": runtime_smoke.ok,
            },
        )

    @staticmethod
    def _check_model_contract() -> CampaignStateAggregateCheck:
        state = CampaignState(campaign_id="aggregate", title="Aggregate Campaign")
        state.locations["town"] = LocationState(location_id="town", name="Town", discovered=True, visited=True)
        state.quests["q1"] = __import__(
            "services.campaign.campaign_state_models",
            fromlist=["QuestState"],
        ).QuestState(quest_id="q1", title="Quest", status=QuestStatus.ACTIVE)
        ok = (
            state.campaign_id == "aggregate"
            and state.locations["town"].visited is True
            and state.quests["q1"].status == QuestStatus.ACTIVE
        )
        return CampaignStateAggregateCheck(
            name="model_contract",
            ok=ok,
            message="Campaign state models support locations and active quests." if ok else "Campaign state model contract failed.",
            details={"locations": list(state.locations.keys()), "quests": list(state.quests.keys())},
        )

    @staticmethod
    def _check_store_contract() -> CampaignStateAggregateCheck:
        store = CampaignStateStore()
        state = CampaignState(campaign_id="aggregate", title="Aggregate Campaign")
        store.save_campaign(state)
        loaded = store.get_campaign("aggregate")
        ok = loaded is state
        return CampaignStateAggregateCheck(
            name="store_contract",
            ok=ok,
            message="CampaignStateStore saves and loads campaign state." if ok else "CampaignStateStore contract failed.",
        )

    @staticmethod
    def _check_application_contract() -> CampaignStateAggregateCheck:
        store = CampaignStateStore()
        service = CampaignTransitionApplicationService(store, approval_policy=CampaignTransitionApprovalPolicy())
        proposal = CampaignStateTransitionProposal(
            proposal_id="aggregate:scene:location-unlocked:tower",
            campaign_id="aggregate",
            scene_id="scene",
            transition_type=CampaignStateTransitionType.LOCATION_UNLOCKED,
            title="Tower unlocked",
            summary="A tower was discovered.",
            risk=CampaignStateTransitionRisk.LOW,
            approval_required=False,
            approval_status=CampaignStateTransitionApprovalStatus.APPROVED,
            state_patch_preview={"location_id": "tower", "title": "Tower"},
        )
        result = service.apply_proposals("aggregate", "scene", [proposal])
        state = store.get_campaign("aggregate")
        ok = result.applied_count == 1 and state is not None and "tower" in state.locations
        return CampaignStateAggregateCheck(
            name="application_contract",
            ok=ok,
            message="Approved transition proposal applies to CampaignStateStore." if ok else "Application contract failed.",
            details={"summary": result.summary, "applied_count": result.applied_count},
        )

    @staticmethod
    def _check_query_contract() -> CampaignStateAggregateCheck:
        store = CampaignStateStore()
        state = CampaignState(campaign_id="aggregate", title="Aggregate Campaign")
        state.locations["tower"] = LocationState(location_id="tower", name="Tower", discovered=True, visited=True)
        state.knowledge.known_locations.append("tower")
        state.knowledge.known_clues.append("The tower is important.")
        store.save_campaign(state)
        service = CampaignStateQueryService(store)
        summary = service.summarize("aggregate")
        ok = "tower" in summary.known_locations and "The tower is important." in summary.known_clues
        return CampaignStateAggregateCheck(
            name="query_contract",
            ok=ok,
            message="CampaignStateQueryService summarizes updated campaign state." if ok else "Query contract failed.",
            details=asdict(summary),
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
