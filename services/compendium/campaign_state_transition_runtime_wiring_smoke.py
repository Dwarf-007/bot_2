"""
SERVICES/COMPENDIUM/CAMPAIGN_STATE_TRANSITION_RUNTIME_WIRING_SMOKE.PY
Runtime wiring smoke for G1 Campaign State Transition Proposal flow.

G1.5 purpose:
- Verify that F3 CampaignContentAdvisor and G1 transition proposal/application
  services can be composed in a runtime-like way.
- Exercise campaign, donjon, sandbox, missing-scene, and never-auto paths.
- Verify TurnOutput remains advisory-only and no campaign state mutation happens.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- No campaign state mutation.
- No automatic state application.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.turn_output import TurnOutput
from services.compendium.campaign_content_advisor import CampaignContentAdvisor
from services.compendium.campaign_state_transition_application_service import (
    CampaignStateTransitionApplicationService,
)
from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionProposal,
    CampaignStateTransitionProposalResult,
    CampaignStateTransitionRisk,
    CampaignStateTransitionType,
)
from services.compendium.campaign_state_transition_proposal_service import (
    CampaignStateTransitionProposalRequest,
    CampaignStateTransitionProposalService,
)
from services.compendium.campaign_transition_approval_policy import CampaignTransitionApprovalPolicy
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.fiveetools_data_source import FiveEToolsDataSource
from services.compendium.module_reference_service import ModuleReferenceQuery, ModuleReferenceService


CANONICAL_G1_RUNTIME_FILES: tuple[str, ...] = (
    "services/compendium/campaign_content_advisor.py",
    "services/compendium/campaign_state_transition_models.py",
    "services/compendium/campaign_state_transition_proposal_service.py",
    "services/compendium/campaign_transition_approval_policy.py",
    "services/compendium/campaign_state_transition_application_service.py",
    "services/compendium/campaign_state_transition_runtime_wiring_smoke.py",
    "services/compendium/module_reference_service.py",
    "services/compendium/compendium_index_service.py",
    "services/compendium/fiveetools_data_source.py",
)

FORBIDDEN_RUNTIME_MARKERS: tuple[str, ...] = (
    "dispatch_commands",
    "AvraeDispatcher(",
    "AvraeClient(",
    ".is_available()",
    "message.channel.send",
)


@dataclass(frozen=True)
class CampaignStateTransitionRuntimeComponents:
    raw_root: Path
    data_source: FiveEToolsDataSource
    index: CompendiumIndexService
    module_reference: ModuleReferenceService
    campaign_content_advisor: CampaignContentAdvisor
    proposal_service: CampaignStateTransitionProposalService
    approval_policy: CampaignTransitionApprovalPolicy
    application_service: CampaignStateTransitionApplicationService


@dataclass(frozen=True)
class CampaignStateTransitionRuntimeSmokeCheck:
    name: str
    ok: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignStateTransitionRuntimeSmokeResult:
    ok: bool
    checks: List[CampaignStateTransitionRuntimeSmokeCheck] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
            "stats": dict(self.stats),
        }

    def summary_text(self) -> str:
        passed = sum(1 for check in self.checks if check.ok)
        lines = [f"CampaignStateTransition runtime wiring smoke: {passed}/{len(self.checks)} passed"]
        for check in self.checks:
            prefix = "OK" if check.ok else "FAIL"
            lines.append(f"- {prefix} {check.name}: {check.message}".rstrip())
        return "\n".join(lines)


class CampaignStateTransitionRuntimeWiringBuilder:
    """Small composition helper for G1 runtime services."""

    def build(self, raw_root: str | Path) -> CampaignStateTransitionRuntimeComponents:
        raw_path = Path(raw_root)
        data_source = FiveEToolsDataSource(raw_root=raw_path)
        entries = data_source.load_entries()
        index = CompendiumIndexService(entries)
        module_reference = ModuleReferenceService(index)
        campaign_content_advisor = CampaignContentAdvisor(module_reference)
        proposal_service = CampaignStateTransitionProposalService()
        approval_policy = CampaignTransitionApprovalPolicy()
        application_service = CampaignStateTransitionApplicationService(
            proposal_service=proposal_service,
            approval_policy=approval_policy,
        )
        return CampaignStateTransitionRuntimeComponents(
            raw_root=raw_path,
            data_source=data_source,
            index=index,
            module_reference=module_reference,
            campaign_content_advisor=campaign_content_advisor,
            proposal_service=proposal_service,
            approval_policy=approval_policy,
            application_service=application_service,
        )


class CampaignStateTransitionRuntimeWiringSmoke:
    """Runs runtime-like smoke checks for the G1 proposal/approval/output flow."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)

    def run(self) -> CampaignStateTransitionRuntimeSmokeResult:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root = Path(tmp) / "raw"
            self._write_fixture_raw_data(raw_root)
            return self.run_against_raw_root(raw_root)

    def run_against_raw_root(self, raw_root: str | Path) -> CampaignStateTransitionRuntimeSmokeResult:
        checks: List[CampaignStateTransitionRuntimeSmokeCheck] = []
        components = CampaignStateTransitionRuntimeWiringBuilder().build(raw_root)
        stats = components.index.stats()

        checks.append(CampaignStateTransitionRuntimeSmokeCheck(
            name="runtime_components_composed",
            ok=stats.entries >= 1 and components.application_service is not None,
            message="Runtime-like G1 transition components were composed." if stats.entries >= 1 else "G1 runtime component composition loaded too few entries.",
            details={"stats": asdict(stats)},
        ))

        campaign_output = self._run_scene_path(
            components=components,
            name="campaign_goblin_ambush_transition_output",
            query="Goblin Ambush",
            campaign_id="lmop-runtime",
            scene_id="goblin-ambush",
            required_public=["Campaign State Transition Advisory", "Goblin Ambush", "DM approval"],
            required_dm=["encounter_suggested", "xp_award_candidate", "Approval policy summary"],
        )
        checks.append(campaign_output)

        donjon_output = self._run_scene_path(
            components=components,
            name="donjon_trap_transition_output",
            query="Trapped Hall",
            campaign_id="lmop-runtime",
            scene_id="redbrand-03",
            required_public=["Campaign State Transition Advisory", "Trap", "DM approval"],
            required_dm=["trap_detected", "State patch preview", "DC 15"],
        )
        checks.append(donjon_output)

        sandbox_output = self._run_scene_path(
            components=components,
            name="sandbox_npc_transition_output",
            query="Important NPCs",
            campaign_id="sandbox-context",
            scene_id="phandalin-npcs",
            required_public=["Campaign State Transition Advisory", "NPC", "DM approval"],
            required_dm=["npc_info_revealed", "Approval policy summary"],
        )
        checks.append(sandbox_output)

        missing_advice = components.campaign_content_advisor.advise(ModuleReferenceQuery(text="Unknown Scene", module_name="Lost Mine"))
        missing_request = CampaignStateTransitionProposalRequest(
            campaign_id="lmop-runtime",
            scene_id="unknown-scene",
            advice=missing_advice,
        )
        missing_output = components.application_service.advise(missing_request)
        checks.append(self._check_turn_output(
            name="missing_scene_transition_output",
            output=missing_output,
            required_public=["Campaign State Transition Advisory", "DM needs"],
            required_dm=["dm_review_required", "Approval policy summary"],
        ))

        never_auto_result = CampaignStateTransitionProposalResult(
            campaign_id="lmop-runtime",
            scene_id="branch-test",
            proposals=[CampaignStateTransitionProposal(
                proposal_id="lmop-runtime:branch-test:branch-selected:forced-branch",
                campaign_id="lmop-runtime",
                scene_id="branch-test",
                transition_type=CampaignStateTransitionType.BRANCH_SELECTED,
                title="Forced branch selection candidate",
                summary="A branch would be selected and should never be auto-applied.",
                risk=CampaignStateTransitionRisk.HIGH,
                approval_required=True,
            )],
        )
        never_auto_output = components.application_service.advise(never_auto_result)
        checks.append(self._check_turn_output(
            name="never_auto_transition_output",
            output=never_auto_output,
            required_public=["never-auto"],
            required_dm=["never_auto", "Blocking reasons"],
        ))

        missing_files, violations = self._scan_no_runtime_coupling(CANONICAL_G1_RUNTIME_FILES, FORBIDDEN_RUNTIME_MARKERS)
        checks.append(CampaignStateTransitionRuntimeSmokeCheck(
            name="canonical_g1_runtime_files_present",
            ok=not missing_files,
            message="All canonical G1 runtime files are present." if not missing_files else "Some canonical G1 runtime files are missing.",
            details={"missing_files": missing_files},
        ))
        checks.append(CampaignStateTransitionRuntimeSmokeCheck(
            name="no_avrae_or_discord_runtime_coupling",
            ok=not violations,
            message="No Avrae/Discord markers found in G1 transition path." if not violations else "Forbidden runtime markers found.",
            details={"violations": violations},
        ))

        return CampaignStateTransitionRuntimeSmokeResult(
            ok=all(check.ok for check in checks),
            checks=checks,
            stats={
                "entries": stats.entries,
                "entry_types": dict(stats.entry_types),
                "raw_root": str(components.raw_root),
            },
        )

    def _run_scene_path(
        self,
        components: CampaignStateTransitionRuntimeComponents,
        name: str,
        query: str,
        campaign_id: str,
        scene_id: str,
        required_public: List[str],
        required_dm: List[str],
    ) -> CampaignStateTransitionRuntimeSmokeCheck:
        advice = components.campaign_content_advisor.advise(ModuleReferenceQuery(text=query, module_name="Lost Mine"))
        proposal_request = CampaignStateTransitionProposalRequest(
            campaign_id=campaign_id,
            scene_id=scene_id,
            advice=advice,
            party_action_summary=f"Runtime smoke requested transition proposals for {query}.",
        )
        output = components.application_service.advise(proposal_request)
        return self._check_turn_output(name=name, output=output, required_public=required_public, required_dm=required_dm)

    @staticmethod
    def _check_turn_output(
        name: str,
        output: TurnOutput,
        required_public: List[str],
        required_dm: List[str],
    ) -> CampaignStateTransitionRuntimeSmokeCheck:
        public_ok = all(fragment in output.public_narrative for fragment in required_public)
        dm_text = "\n".join(output.dm_instructions)
        dm_ok = all(fragment in dm_text for fragment in required_dm)
        ok = (
            isinstance(output, TurnOutput)
            and bool(output.public_narrative.strip())
            and output.suggested_commands == []
            and output.avrae_commands == []
            and bool(output.dm_instructions)
            and public_ok
            and dm_ok
        )
        return CampaignStateTransitionRuntimeSmokeCheck(
            name=name,
            ok=ok,
            message="G1 application service returned advisory TurnOutput." if ok else "G1 TurnOutput did not satisfy runtime contract.",
            details={
                "public_narrative": output.public_narrative,
                "dm_instructions": list(output.dm_instructions),
                "debug_notes": list(output.debug_notes),
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

    @staticmethod
    def _write_fixture_raw_data(raw_root: Path) -> None:
        (raw_root / "adventures").mkdir(parents=True, exist_ok=True)
        _write_json(raw_root / "adventures" / "adventure-lmop-g1-smoke.json", {
            "adventure": [{
                "name": "Lost Mine Sample",
                "source": "LMOP",
                "id": "LMOP-G1-SMOKE",
                "entries": [
                    {
                        "type": "entries",
                        "name": "Goblin Ambush",
                        "entries": [
                            {"type": "insetReadaloud", "entries": ["Two dead horses block the path ahead."]},
                            "Four {@creature goblin||goblins} are hiding in the woods and attack.",
                            "{@b Developments}",
                            "The characters might capture goblins and learn where the trail leads.",
                            {"type": "entries", "name": "Awarding Experience Points", "entries": ["Award 75 XP when the party completes the ambush milestone."]},
                        ],
                    },
                    {
                        "type": "entries",
                        "name": "3. Trapped Hall",
                        "entries": [
                            "A hidden pit trap lies under loose stone tiles.",
                            "A successful {@dc 15} Wisdom ({@skill Perception}) check spots the trap.",
                            "On a failed save, the creature takes {@damage 2d6} bludgeoning damage and lands {@condition prone}.",
                        ],
                    },
                    {
                        "type": "entries",
                        "name": "Important NPCs",
                        "entries": [
                            {"type": "table", "rows": [["Toblen Stonehill", "Innkeeper."], ["Daran Edermath", "Member of the Order of the Gauntlet with a quest for the party."]]},
                        ],
                    },
                ],
            }]
        })


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
