"""
SERVICES/COMPENDIUM/CHARACTER_CREATION_AGGREGATE_GATE.PY
Aggregate gate for the F2 CharacterCreationAdvisor MVP line.

F2.5 purpose:
- Close the F2.1-F2.4 CharacterCreationAdvisor MVP slice.
- Run/adapt the F2.2 smoke gate and F2.4 runtime wiring smoke.
- Verify the runtime-facing application service returns canonical TurnOutput.
- Verify advisory-only/no Avrae/Discord coupling invariants.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No D&D Beyond integration.
- No LLM calls.
- No database dependency.
- Does not mutate character sheets.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.turn_output import TurnOutput
from services.compendium.character_creation_application_service import CharacterCreationApplicationRequest
from services.compendium.character_creation_runtime_wiring_smoke import (
    CharacterCreationRuntimeWiringBuilder,
    CharacterCreationRuntimeWiringSmoke,
)
from services.compendium.character_creation_smoke_gate import CharacterCreationSmokeGate


CANONICAL_F2_FILES: tuple[str, ...] = (
    "services/compendium/character_creation_advisor.py",
    "services/compendium/character_creation_application_service.py",
    "services/compendium/character_creation_smoke_gate.py",
    "services/compendium/character_creation_runtime_wiring_smoke.py",
    "services/compendium/character_option_service.py",
    "services/compendium/level_up_advisor.py",
    "services/compendium/spell_reference_service.py",
    "services/compendium/rules_reference_service.py",
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
class CharacterCreationAggregateCheck:
    name: str
    ok: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CharacterCreationAggregateResult:
    ok: bool
    checks: List[CharacterCreationAggregateCheck] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
            "stats": dict(self.stats),
        }

    def summary_text(self) -> str:
        passed = sum(1 for check in self.checks if check.ok)
        lines = [f"CharacterCreation F2 aggregate gate: {passed}/{len(self.checks)} passed"]
        for check in self.checks:
            prefix = "OK" if check.ok else "FAIL"
            lines.append(f"- {prefix} {check.name}: {check.message}".rstrip())
        return "
".join(lines)


class CharacterCreationAggregateGate:
    """Runs the F2 CharacterCreationAdvisor aggregate gate."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)

    def run(self) -> CharacterCreationAggregateResult:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root = Path(tmp) / "raw"
            CharacterCreationRuntimeWiringSmoke._write_fixture_raw_data(raw_root)
            return self.run_against_raw_root(raw_root)

    def run_against_raw_root(self, raw_root: str | Path) -> CharacterCreationAggregateResult:
        raw_root = Path(raw_root)
        checks: List[CharacterCreationAggregateCheck] = []

        smoke_result = CharacterCreationSmokeGate(project_root=self.project_root).run_against_raw_root(raw_root)
        checks.append(CharacterCreationAggregateCheck(
            name="f2_02_character_creation_smoke_gate",
            ok=smoke_result.ok,
            message="F2.2 CharacterCreationAdvisor smoke gate passed." if smoke_result.ok else "F2.2 smoke gate failed.",
            details={"summary": smoke_result.summary_text(), "stats": dict(smoke_result.stats)},
        ))

        wiring_result = CharacterCreationRuntimeWiringSmoke(project_root=self.project_root).run_against_raw_root(raw_root)
        checks.append(CharacterCreationAggregateCheck(
            name="f2_04_runtime_wiring_smoke",
            ok=wiring_result.ok,
            message="F2.4 runtime wiring smoke passed." if wiring_result.ok else "F2.4 runtime wiring smoke failed.",
            details={"summary": wiring_result.summary_text(), "stats": dict(wiring_result.stats)},
        ))

        components = CharacterCreationRuntimeWiringBuilder().build(raw_root)
        output = components.application_service.advise(CharacterCreationApplicationRequest(
            concept="aggregate donjon scout",
            selected_class="Rogue",
            selected_species="Human",
            selected_background="Soldier",
            preferred_role="scout",
            ability_score_method="standard array",
            include_donjon_readiness=True,
            include_sandbox_readiness=True,
            requester_id="aggregate-user",
            channel_id="aggregate-channel",
        ))
        checks.append(self._check_turn_output_contract(output))

        missing_files, violations = self._scan_no_runtime_coupling(CANONICAL_F2_FILES, FORBIDDEN_RUNTIME_MARKERS)
        checks.append(CharacterCreationAggregateCheck(
            name="canonical_f2_files_present",
            ok=not missing_files,
            message="All canonical F2 character creation files are present." if not missing_files else "Some canonical F2 files are missing.",
            details={"missing_files": missing_files},
        ))
        checks.append(CharacterCreationAggregateCheck(
            name="no_avrae_or_discord_runtime_coupling",
            ok=not violations,
            message="No Avrae/Discord markers found in F2 character creation path." if not violations else "Forbidden runtime markers found.",
            details={"violations": violations},
        ))

        index_stats = components.index.stats()
        result_stats = {
            "entries": index_stats.entries,
            "entry_types": dict(index_stats.entry_types),
            "raw_root": str(raw_root),
            "f2_02_ok": smoke_result.ok,
            "f2_04_ok": wiring_result.ok,
        }
        return CharacterCreationAggregateResult(ok=all(check.ok for check in checks), checks=checks, stats=result_stats)

    @staticmethod
    def _check_turn_output_contract(output: TurnOutput) -> CharacterCreationAggregateCheck:
        ok = (
            isinstance(output, TurnOutput)
            and bool(output.public_narrative.strip())
            and "Character Creation Advisory" in output.public_narrative
            and "Rogue" in output.public_narrative
            and "Donjon readiness" in output.public_narrative
            and "Sandbox readiness" in output.public_narrative
            and output.suggested_commands == []
            and output.avrae_commands == []
            and bool(output.dm_instructions)
        )
        return CharacterCreationAggregateCheck(
            name="application_turn_output_contract",
            ok=ok,
            message="CharacterCreationApplicationService returned canonical advisory TurnOutput." if ok else "TurnOutput contract check failed.",
            details={
                "public_narrative": output.public_narrative,
                "dm_instructions": list(output.dm_instructions),
                "debug_notes": list(output.debug_notes),
                "suggested_commands": list(output.suggested_commands),
                "avrae_commands": list(output.avrae_commands),
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
