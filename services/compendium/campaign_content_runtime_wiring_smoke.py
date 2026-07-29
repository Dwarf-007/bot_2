"""
SERVICES/COMPENDIUM/CAMPAIGN_CONTENT_RUNTIME_WIRING_SMOKE.PY
Runtime wiring smoke for F3 Campaign Content Foundation.

F3.5 purpose:
- Verify that ModuleReferenceService, CampaignContentAdvisor, and
  CampaignContentApplicationService can be composed in a runtime-like way.
- Exercise campaign, donjon, and sandbox payloads.
- Verify TurnOutput remains advisory-only and contains no Avrae/Discord runtime
  coupling.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- Does not reproduce long adventure/book text.
- Does not mutate campaign state.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.turn_output import TurnOutput
from services.compendium.campaign_content_advisor import CampaignContentAdvisor
from services.compendium.campaign_content_application_service import (
    CampaignContentApplicationRequest,
    CampaignContentApplicationService,
)
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.fiveetools_data_source import FiveEToolsDataSource
from services.compendium.module_reference_service import ModuleReferenceService


CANONICAL_F3_RUNTIME_FILES: tuple[str, ...] = (
    "services/compendium/module_reference_service.py",
    "services/compendium/module_reference_application_service.py",
    "services/compendium/campaign_content_advisor.py",
    "services/compendium/campaign_content_application_service.py",
    "services/compendium/campaign_content_runtime_wiring_smoke.py",
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
class CampaignContentRuntimeComponents:
    raw_root: Path
    data_source: FiveEToolsDataSource
    index: CompendiumIndexService
    module_reference: ModuleReferenceService
    campaign_advisor: CampaignContentAdvisor
    application_service: CampaignContentApplicationService


@dataclass(frozen=True)
class CampaignContentRuntimeSmokeCheck:
    name: str
    ok: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignContentRuntimeSmokeResult:
    ok: bool
    checks: List[CampaignContentRuntimeSmokeCheck] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
            "stats": dict(self.stats),
        }

    def summary_text(self) -> str:
        passed = sum(1 for check in self.checks if check.ok)
        lines = [f"CampaignContent runtime wiring smoke: {passed}/{len(self.checks)} passed"]
        for check in self.checks:
            prefix = "OK" if check.ok else "FAIL"
            lines.append(f"- {prefix} {check.name}: {check.message}".rstrip())
        return "
".join(lines)


class CampaignContentRuntimeWiringBuilder:
    """Small composition helper for campaign content runtime services."""

    def build(self, raw_root: str | Path) -> CampaignContentRuntimeComponents:
        raw_path = Path(raw_root)
        data_source = FiveEToolsDataSource(raw_root=raw_path)
        entries = data_source.load_entries()
        index = CompendiumIndexService(entries)
        module_reference = ModuleReferenceService(index)
        campaign_advisor = CampaignContentAdvisor(module_reference)
        application_service = CampaignContentApplicationService(campaign_advisor)
        return CampaignContentRuntimeComponents(
            raw_root=raw_path,
            data_source=data_source,
            index=index,
            module_reference=module_reference,
            campaign_advisor=campaign_advisor,
            application_service=application_service,
        )


class CampaignContentRuntimeWiringSmoke:
    """Runs a runtime-like wiring smoke for F3 campaign content services."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)

    def run(self) -> CampaignContentRuntimeSmokeResult:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root = Path(tmp) / "raw"
            self._write_fixture_raw_data(raw_root)
            return self.run_against_raw_root(raw_root)

    def run_against_raw_root(self, raw_root: str | Path) -> CampaignContentRuntimeSmokeResult:
        checks: List[CampaignContentRuntimeSmokeCheck] = []
        components = CampaignContentRuntimeWiringBuilder().build(raw_root)
        stats = components.index.stats()

        checks.append(CampaignContentRuntimeSmokeCheck(
            name="runtime_components_composed",
            ok=stats.entries >= 1 and components.application_service is not None,
            message="Runtime-like campaign content components were composed." if stats.entries >= 1 else "Runtime component composition loaded too few entries.",
            details={"stats": asdict(stats)},
        ))

        campaign_output = components.application_service.advise(CampaignContentApplicationRequest(
            query="Goblin Ambush",
            module_name="Lost Mine",
            campaign_id="lmop-runtime",
            scene_id="goblin-ambush",
            include_player_summary=True,
            include_read_aloud_candidate=True,
        ))
        checks.append(self._check_turn_output(
            name="campaign_scene_turn_output",
            output=campaign_output,
            required_fragments=["Campaign Content Advisory", "Goblin Ambush", "Read-aloud candidate", "DM approval"],
            required_dm_fragments=["Encounter hints", "Approval checkpoints"],
        ))

        donjon_output = components.application_service.advise({
            "location": "Trapped Hall",
            "module": "Lost Mine",
            "campaign_id": "lmop-runtime",
            "room_id": "redbrand-03",
            "audience": "dm",
        })
        checks.append(self._check_turn_output(
            name="donjon_room_trap_turn_output",
            output=donjon_output,
            required_fragments=["Campaign Content Advisory", "trap mechanics", "DM approval"],
            required_dm_fragments=["Trap hints", "DC 15", "2d6"],
        ))

        sandbox_output = components.application_service.advise({
            "scene": "Important NPCs",
            "module": "Lost Mine",
            "campaign_id": "sandbox-context",
            "scene_id": "phandalin-npcs",
            "include_player_summary": True,
        })
        checks.append(self._check_turn_output(
            name="sandbox_npc_context_turn_output",
            output=sandbox_output,
            required_fragments=["Campaign Content Advisory", "sandbox-context", "DM approval"],
            required_dm_fragments=["NPC hints"],
        ))

        missing_output = components.application_service.advise("Unknown Scene")
        checks.append(self._check_turn_output(
            name="missing_scene_turn_output",
            output=missing_output,
            required_fragments=["No matching campaign content was found"],
            required_dm_fragments=["No matching module node"],
        ))

        missing_files, violations = self._scan_no_runtime_coupling(CANONICAL_F3_RUNTIME_FILES, FORBIDDEN_RUNTIME_MARKERS)
        checks.append(CampaignContentRuntimeSmokeCheck(
            name="canonical_f3_runtime_files_present",
            ok=not missing_files,
            message="All canonical F3 runtime files are present." if not missing_files else "Some canonical F3 runtime files are missing.",
            details={"missing_files": missing_files},
        ))
        checks.append(CampaignContentRuntimeSmokeCheck(
            name="no_avrae_or_discord_runtime_coupling",
            ok=not violations,
            message="No Avrae/Discord markers found in F3 campaign content path." if not violations else "Forbidden runtime markers found.",
            details={"violations": violations},
        ))

        return CampaignContentRuntimeSmokeResult(
            ok=all(check.ok for check in checks),
            checks=checks,
            stats={
                "entries": stats.entries,
                "entry_types": dict(stats.entry_types),
                "raw_root": str(components.raw_root),
            },
        )

    @staticmethod
    def _check_turn_output(
        name: str,
        output: TurnOutput,
        required_fragments: List[str],
        required_dm_fragments: List[str],
    ) -> CampaignContentRuntimeSmokeCheck:
        public_ok = all(fragment in output.public_narrative for fragment in required_fragments)
        dm_text = "
".join(output.dm_instructions)
        dm_ok = all(fragment in dm_text for fragment in required_dm_fragments)
        ok = (
            isinstance(output, TurnOutput)
            and bool(output.public_narrative.strip())
            and output.suggested_commands == []
            and output.avrae_commands == []
            and bool(output.dm_instructions)
            and public_ok
            and dm_ok
        )
        return CampaignContentRuntimeSmokeCheck(
            name=name,
            ok=ok,
            message="Campaign content application service returned advisory TurnOutput." if ok else "TurnOutput did not satisfy F3 runtime contract.",
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
        _write_json(raw_root / "adventures" / "adventure-lmop-smoke.json", {
            "adventure": [{
                "name": "Lost Mine Sample",
                "source": "LMOP",
                "id": "LMOP-SMOKE",
                "entries": [
                    {
                        "type": "entries",
                        "name": "Goblin Ambush",
                        "entries": [
                            {"type": "insetReadaloud", "entries": ["Two dead horses block the path ahead."]},
                            "Four {@creature goblin||goblins} are hiding in the woods and attack.",
                            "{@b Developments}",
                            "The characters might capture goblins and learn where the trail leads.",
                        ],
                    },
                    {
                        "type": "entries",
                        "name": "3. Trapped Hall",
                        "entries": [
                            "A hidden pit trap lies under loose stone tiles.",
                            "A successful {@dc 15} Wisdom ({@skill Perception}) check spots the trap.",
                            "On a failed save, the creature takes {@damage 2d6} bludgeoning damage and lands {@condition prone}.",
                            {"type": "entries", "name": "Awarding Experience Points", "entries": ["Divide 100 XP equally if the party survives."]},
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
