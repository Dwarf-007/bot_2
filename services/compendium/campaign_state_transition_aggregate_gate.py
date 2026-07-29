"""
SERVICES/COMPENDIUM/CAMPAIGN_STATE_TRANSITION_AGGREGATE_GATE.PY
Aggregate gate for the G1 Campaign State Transition Proposal line.

G1.6 purpose:
- Close the G1.1-G1.5 Campaign State Transition MVP slice.
- Run/adapt the G1.5 runtime wiring smoke.
- Verify proposal generation, approval policy, TurnOutput mapping, and safety invariants.
- Verify no campaign state mutation, no Avrae/Discord coupling, and no automatic application.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- No campaign state mutation.
- No automatic state application.
"""

from __future__ import annotations

import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.turn_output import TurnOutput
from services.compendium.campaign_state_transition_application_service import CampaignStateTransitionApplicationService
from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionProposal,
    CampaignStateTransitionProposalResult,
    CampaignStateTransitionRisk,
    CampaignStateTransitionType,
)
from services.compendium.campaign_state_transition_runtime_wiring_smoke import (
    CampaignStateTransitionRuntimeWiringBuilder,
    CampaignStateTransitionRuntimeWiringSmoke,
)
from services.compendium.campaign_transition_approval_policy import CampaignTransitionApprovalCategory


CANONICAL_G1_FILES: tuple[str, ...] = (
    "services/compendium/campaign_state_transition_models.py",
    "services/compendium/campaign_state_transition_proposal_service.py",
    "services/compendium/campaign_transition_approval_policy.py",
    "services/compendium/campaign_state_transition_application_service.py",
    "services/compendium/campaign_state_transition_runtime_wiring_smoke.py",
    "services/compendium/campaign_state_transition_aggregate_gate.py",
    "services/compendium/campaign_content_advisor.py",
    "services/compendium/module_reference_service.py",
)

FORBIDDEN_RUNTIME_MARKERS: tuple[str, ...] = (
    "dispatch_commands",
    "AvraeDispatcher(",
    "AvraeClient(",
    ".is_available()",
    "message.channel.send",
)

FORBIDDEN_STATE_MUTATION_MARKERS: tuple[str, ...] = (
    ".save(",
    ".commit(",
    "write_state(",
    "apply_state_patch(",
    "mutate_campaign_state(",
    "campaign_state_store.apply",
)


@dataclass(frozen=True)
class CampaignStateTransitionAggregateCheck:
    name: str
    ok: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignStateTransitionAggregateResult:
    ok: bool
    checks: List[CampaignStateTransitionAggregateCheck] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
            "stats": dict(self.stats),
        }

    def summary_text(self) -> str:
        passed = sum(1 for check in self.checks if check.ok)
        lines = [f"CampaignStateTransition G1 aggregate gate: {passed}/{len(self.checks)} passed"]
        for check in self.checks:
            prefix = "OK" if check.ok else "FAIL"
            lines.append(f"- {prefix} {check.name}: {check.message}".rstrip())
        return "\n".join(lines)


class CampaignStateTransitionAggregateGate:
    """Runs the G1 Campaign State Transition aggregate gate."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)

    def run(self) -> CampaignStateTransitionAggregateResult:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root = Path(tmp) / "raw"
            CampaignStateTransitionRuntimeWiringSmoke._write_fixture_raw_data(raw_root)
            return self.run_against_raw_root(raw_root)

    def run_against_raw_root(self, raw_root: str | Path) -> CampaignStateTransitionAggregateResult:
        raw_root = Path(raw_root)
        checks: List[CampaignStateTransitionAggregateCheck] = []

        runtime_result = CampaignStateTransitionRuntimeWiringSmoke(project_root=self.project_root).run_against_raw_root(raw_root)
        checks.append(CampaignStateTransitionAggregateCheck(
            name="g1_05_runtime_wiring_smoke",
            ok=runtime_result.ok,
            message="G1.5 runtime wiring smoke passed." if runtime_result.ok else "G1.5 runtime wiring smoke failed.",
            details={"summary": runtime_result.summary_text(), "stats": dict(runtime_result.stats)},
        ))

        components = CampaignStateTransitionRuntimeWiringBuilder().build(raw_root)
        goblin_advice = components.campaign_content_advisor.advise("Goblin Ambush")
        proposal_result = components.proposal_service.propose(
            __import__(
                "services.compendium.campaign_state_transition_proposal_service",
                fromlist=["CampaignStateTransitionProposalRequest"],
            ).CampaignStateTransitionProposalRequest(
                campaign_id="lmop-aggregate",
                scene_id="goblin-ambush",
                advice=goblin_advice,
                party_action_summary="Aggregate gate asks for next campaign transition candidates.",
            )
        )
        decisions = components.approval_policy.decide_batch(proposal_result.proposals)
        output = components.application_service.advise(proposal_result)

        checks.append(self._check_proposal_generation_contract(proposal_result))
        checks.append(self._check_approval_policy_contract(decisions))
        checks.append(self._check_application_turn_output_contract(output))
        checks.append(self._check_never_auto_contract())

        missing_files, runtime_violations = self._scan_markers(CANONICAL_G1_FILES, FORBIDDEN_RUNTIME_MARKERS)
        _, mutation_violations = self._scan_markers(CANONICAL_G1_FILES, FORBIDDEN_STATE_MUTATION_MARKERS)
        checks.append(CampaignStateTransitionAggregateCheck(
            name="canonical_g1_files_present",
            ok=not missing_files,
            message="All canonical G1 files are present." if not missing_files else "Some canonical G1 files are missing.",
            details={"missing_files": missing_files},
        ))
        checks.append(CampaignStateTransitionAggregateCheck(
            name="no_avrae_or_discord_runtime_coupling",
            ok=not runtime_violations,
            message="No Avrae/Discord markers found in G1 transition path." if not runtime_violations else "Forbidden runtime markers found.",
            details={"violations": runtime_violations},
        ))
        checks.append(CampaignStateTransitionAggregateCheck(
            name="no_campaign_state_mutation",
            ok=not mutation_violations,
            message="No campaign state mutation markers found in G1 proposal/application path." if not mutation_violations else "State mutation markers found.",
            details={"violations": mutation_violations},
        ))

        stats = components.index.stats()
        return CampaignStateTransitionAggregateResult(
            ok=all(check.ok for check in checks),
            checks=checks,
            stats={
                "entries": stats.entries,
                "entry_types": dict(stats.entry_types),
                "raw_root": str(raw_root),
                "g1_05_ok": runtime_result.ok,
                "proposal_count": len(proposal_result.proposals),
                "approval_decisions": len(decisions.decisions),
            },
        )

    @staticmethod
    def _check_proposal_generation_contract(result: CampaignStateTransitionProposalResult) -> CampaignStateTransitionAggregateCheck:
        types = {str(proposal.transition_type.value if hasattr(proposal.transition_type, "value") else proposal.transition_type) for proposal in result.proposals}
        ok = (
            result.ok
            and result.approval_required
            and "encounter_suggested" in types
            and "xp_award_candidate" in types
            and all(proposal.evidence for proposal in result.proposals)
        )
        return CampaignStateTransitionAggregateCheck(
            name="proposal_generation_contract",
            ok=ok,
            message="Proposal service generated evidence-backed transition proposals." if ok else "Proposal generation contract failed.",
            details={"types": sorted(types), "proposal_count": len(result.proposals), "summary": result.summary},
        )

    @staticmethod
    def _check_approval_policy_contract(decisions) -> CampaignStateTransitionAggregateCheck:
        categories = {str(decision.category.value if hasattr(decision.category, "value") else decision.category) for decision in decisions.decisions}
        ok = decisions.requires_dm_approval and "dm_approval_required" in categories
        return CampaignStateTransitionAggregateCheck(
            name="approval_policy_contract",
            ok=ok,
            message="Approval policy requires DM review for state-changing proposals." if ok else "Approval policy contract failed.",
            details=decisions.to_dict(),
        )

    @staticmethod
    def _check_application_turn_output_contract(output: TurnOutput) -> CampaignStateTransitionAggregateCheck:
        dm_text = "\n".join(output.dm_instructions)
        ok = (
            isinstance(output, TurnOutput)
            and "Campaign State Transition Advisory" in output.public_narrative
            and "DM approval" in output.public_narrative
            and "Approval policy summary" in dm_text
            and "Evidence" in dm_text
            and output.suggested_commands == []
            and output.avrae_commands == []
        )
        return CampaignStateTransitionAggregateCheck(
            name="application_turn_output_contract",
            ok=ok,
            message="G1 application service returned canonical advisory TurnOutput." if ok else "TurnOutput contract check failed.",
            details={
                "public_narrative": output.public_narrative,
                "dm_instructions": list(output.dm_instructions),
                "debug_notes": list(output.debug_notes),
                "suggested_commands": list(output.suggested_commands),
                "avrae_commands": list(output.avrae_commands),
            },
        )

    @staticmethod
    def _check_never_auto_contract() -> CampaignStateTransitionAggregateCheck:
        proposal = CampaignStateTransitionProposal(
            proposal_id="aggregate:branch:branch-selected:forced",
            campaign_id="aggregate",
            scene_id="branch",
            transition_type=CampaignStateTransitionType.BRANCH_SELECTED,
            title="Forced branch selection",
            summary="This proposal must never be auto-applied.",
            risk=CampaignStateTransitionRisk.HIGH,
            approval_required=True,
        )
        output = CampaignStateTransitionApplicationService().advise(
            CampaignStateTransitionProposalResult(campaign_id="aggregate", scene_id="branch", proposals=[proposal])
        )
        dm_text = "\n".join(output.dm_instructions)
        ok = "never-auto" in output.public_narrative and "never_auto" in dm_text and output.suggested_commands == []
        return CampaignStateTransitionAggregateCheck(
            name="never_auto_contract",
            ok=ok,
            message="Never-auto proposals are visible and blocked from automatic application." if ok else "Never-auto contract failed.",
            details={"public_narrative": output.public_narrative, "dm_instructions": list(output.dm_instructions)},
        )

    def _scan_markers(self, files: Iterable[str], markers: Iterable[str]) -> tuple[List[str], List[Dict[str, str]]]:
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
