"""
SERVICES/COMPENDIUM/CAMPAIGN_CONTENT_AGGREGATE_GATE.PY
Aggregate gate for the F3 Campaign Content Foundation.

F3.6 purpose:
- Close the F3.1-F3.5 Campaign Content MVP slice.
- Run/adapt the runtime wiring smoke from F3.5.
- Verify campaign content application output remains canonical TurnOutput.
- Verify player-safe/DM-only separation and approval checkpoints.
- Verify advisory-only/no Avrae/Discord coupling invariants.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- Does not reproduce long adventure/book text.
- Does not mutate campaign state.
"""

from __future__ import annotations

import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.turn_output import TurnOutput
from services.compendium.campaign_content_application_service import CampaignContentApplicationRequest
from services.compendium.campaign_content_runtime_wiring_smoke import (
    CampaignContentRuntimeWiringBuilder,
    CampaignContentRuntimeWiringSmoke,
)


CANONICAL_F3_FILES: tuple[str, ...] = (
    "services/compendium/module_reference_service.py",
    "services/compendium/module_reference_application_service.py",
    "services/compendium/campaign_content_advisor.py",
    "services/compendium/campaign_content_application_service.py",
    "services/compendium/campaign_content_runtime_wiring_smoke.py",
    "services/compendium/campaign_content_aggregate_gate.py",
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
class CampaignContentAggregateCheck:
    name: str
    ok: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignContentAggregateResult:
    ok: bool
    checks: List[CampaignContentAggregateCheck] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
            "stats": dict(self.stats),
        }

    def summary_text(self) -> str:
        passed = sum(1 for check in self.checks if check.ok)
        lines = [f"CampaignContent F3 aggregate gate: {passed}/{len(self.checks)} passed"]
        for check in self.checks:
            prefix = "OK" if check.ok else "FAIL"
            lines.append(f"- {prefix} {check.name}: {check.message}".rstrip())
        return "
".join(lines)


class CampaignContentAggregateGate:
    """Runs the F3 Campaign Content aggregate gate."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)

    def run(self) -> CampaignContentAggregateResult:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root = Path(tmp) / "raw"
            CampaignContentRuntimeWiringSmoke._write_fixture_raw_data(raw_root)
            return self.run_against_raw_root(raw_root)

    def run_against_raw_root(self, raw_root: str | Path) -> CampaignContentAggregateResult:
        raw_root = Path(raw_root)
        checks: List[CampaignContentAggregateCheck] = []

        runtime_result = CampaignContentRuntimeWiringSmoke(project_root=self.project_root).run_against_raw_root(raw_root)
        checks.append(CampaignContentAggregateCheck(
            name="f3_05_runtime_wiring_smoke",
            ok=runtime_result.ok,
            message="F3.5 runtime wiring smoke passed." if runtime_result.ok else "F3.5 runtime wiring smoke failed.",
            details={"summary": runtime_result.summary_text(), "stats": dict(runtime_result.stats)},
        ))

        components = CampaignContentRuntimeWiringBuilder().build(raw_root)
        output = components.application_service.advise(CampaignContentApplicationRequest(
            query="Goblin Ambush",
            module_name="Lost Mine",
            campaign_id="f3-aggregate",
            scene_id="goblin-ambush",
            include_player_summary=True,
            include_read_aloud_candidate=True,
            include_dm_only_context=True,
            include_approval_checkpoints=True,
        ))
        checks.append(self._check_turn_output_contract(output))
        checks.append(self._check_player_safe_dm_only_separation(output))
        checks.append(self._check_approval_checkpoint_contract(output))

        missing_output = components.application_service.advise("Unknown Scene")
        checks.append(CampaignContentAggregateCheck(
            name="missing_scene_contract",
            ok=(
                isinstance(missing_output, TurnOutput)
                and "No matching campaign content was found" in missing_output.public_narrative
                and missing_output.suggested_commands == []
                and missing_output.avrae_commands == []
            ),
            message="Missing scene returns safe advisory TurnOutput." if "No matching campaign content was found" in missing_output.public_narrative else "Missing scene output contract failed.",
            details={"public_narrative": missing_output.public_narrative, "dm_instructions": list(missing_output.dm_instructions)},
        ))

        missing_files, violations = self._scan_no_runtime_coupling(CANONICAL_F3_FILES, FORBIDDEN_RUNTIME_MARKERS)
        checks.append(CampaignContentAggregateCheck(
            name="canonical_f3_files_present",
            ok=not missing_files,
            message="All canonical F3 files are present." if not missing_files else "Some canonical F3 files are missing.",
            details={"missing_files": missing_files},
        ))
        checks.append(CampaignContentAggregateCheck(
            name="no_avrae_or_discord_runtime_coupling",
            ok=not violations,
            message="No Avrae/Discord markers found in F3 campaign content path." if not violations else "Forbidden runtime markers found.",
            details={"violations": violations},
        ))

        index_stats = components.index.stats()
        return CampaignContentAggregateResult(
            ok=all(check.ok for check in checks),
            checks=checks,
            stats={
                "entries": index_stats.entries,
                "entry_types": dict(index_stats.entry_types),
                "raw_root": str(raw_root),
                "f3_05_ok": runtime_result.ok,
            },
        )

    @staticmethod
    def _check_turn_output_contract(output: TurnOutput) -> CampaignContentAggregateCheck:
        ok = (
            isinstance(output, TurnOutput)
            and bool(output.public_narrative.strip())
            and "Campaign Content Advisory" in output.public_narrative
            and output.suggested_commands == []
            and output.avrae_commands == []
            and bool(output.dm_instructions)
            and bool(output.debug_notes)
        )
        return CampaignContentAggregateCheck(
            name="application_turn_output_contract",
            ok=ok,
            message="CampaignContentApplicationService returned canonical advisory TurnOutput." if ok else "TurnOutput contract check failed.",
            details={
                "public_narrative": output.public_narrative,
                "dm_instructions": list(output.dm_instructions),
                "debug_notes": list(output.debug_notes),
                "suggested_commands": list(output.suggested_commands),
                "avrae_commands": list(output.avrae_commands),
            },
        )

    @staticmethod
    def _check_player_safe_dm_only_separation(output: TurnOutput) -> CampaignContentAggregateCheck:
        public = output.public_narrative
        dm_text = "
".join(output.dm_instructions)
        ok = (
            "Player-safe summary" in public
            and "DM-only content detected" in public
            and "DM-only" not in public.split("DM-only content detected", 1)[0]
            and "Encounter hints" in dm_text
            and "Reference" not in public[:80]
        )
        return CampaignContentAggregateCheck(
            name="player_safe_dm_only_separation",
            ok=ok,
            message="Player-safe narrative and DM-only context are separated." if ok else "Player-safe/DM-only separation check failed.",
            details={"public_narrative": public, "dm_instructions": list(output.dm_instructions)},
        )

    @staticmethod
    def _check_approval_checkpoint_contract(output: TurnOutput) -> CampaignContentAggregateCheck:
        text = "
".join(output.dm_instructions)
        required = [
            "Approval checkpoints",
            "DM approval",
            "combat",
        ]
        ok = all(item.lower() in text.lower() for item in required)
        return CampaignContentAggregateCheck(
            name="approval_checkpoint_contract",
            ok=ok,
            message="Approval checkpoints are present for state-changing content." if ok else "Approval checkpoint contract failed.",
            details={"dm_instructions": list(output.dm_instructions)},
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
