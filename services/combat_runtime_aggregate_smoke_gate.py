"""
SERVICES/COMBAT_RUNTIME_AGGREGATE_SMOKE_GATE.PY
Aggregate C5 smoke gate for the refactored advisory Combat Runtime.

Purpose:
- Run the C5.1 CombatRuntimeSmokeService.
- Sweep canonical combat files for forbidden Avrae auto-dispatch markers.
- Sweep canonical event handlers for legacy type="avrae_command" producers.
- Provide machine-readable and human-readable aggregate results.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from services.combat_runtime_smoke_service import CombatRuntimeSmokeService


CANONICAL_COMBAT_FILES: tuple[str, ...] = (
    "app/bootstrap.py",
    "bot/bot_core.py",
    "bot/discord_router.py",
    "core/turn_output.py",
    "services/dm_combat_service.py",
    "services/combat_session_service.py",
    "services/monster_decision_service.py",
    "services/combat_recommendation_builder.py",
    "services/combat_dice_service.py",
    "services/combat_runtime_smoke_service.py",
    "services/combat_start_service.py",
    "services/combat_event_handler.py",
    "services/damage_event_handler.py",
    "services/combat_feedback_service.py",
    "services/encounter_service.py",
)

FORBIDDEN_AUTO_DISPATCH_MARKERS: tuple[str, ...] = (
    "dispatch_commands",
    "AvraeDispatcher(",
    "AvraeClient(",
    ".is_available()",
)

LEGACY_AVRAE_COMMAND_MARKERS: tuple[str, ...] = (
    '"type": "avrae_command"',
    "'type': 'avrae_command'",
)


@dataclass(frozen=True)
class AggregateSmokeCheck:
    name: str
    ok: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AggregateSmokeGateResult:
    ok: bool
    checks: List[AggregateSmokeCheck] = field(default_factory=list)
    smoke_result: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
            "smoke_result": self.smoke_result,
        }

    def summary_text(self) -> str:
        passed = sum(1 for check in self.checks if check.ok)
        lines = [f"Combat Runtime aggregate smoke gate: {passed}/{len(self.checks)} passed"]
        for check in self.checks:
            prefix = "OK" if check.ok else "FAIL"
            lines.append(f"- {prefix} {check.name}: {check.message}".rstrip())
        return "
".join(lines)


class CombatRuntimeAggregateSmokeGate:
    """Runs the aggregate C5 combat runtime smoke gate."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)

    def run(self, channel_id: str = "combat-aggregate-smoke") -> AggregateSmokeGateResult:
        checks: List[AggregateSmokeCheck] = []

        smoke = CombatRuntimeSmokeService().run(channel_id=channel_id)
        checks.append(AggregateSmokeCheck(
            name="combat_runtime_smoke_service",
            ok=smoke.ok,
            message="C5.1 CombatRuntimeSmokeService completed." if smoke.ok else "C5.1 smoke failed.",
            details={"summary": smoke.summary_text()},
        ))
        checks.append(AggregateSmokeCheck(
            name="combat_runtime_no_legacy_avrae_commands",
            ok=bool(smoke.no_legacy_avrae_commands),
            message="Smoke outputs did not use legacy avrae_commands." if smoke.no_legacy_avrae_commands else "Smoke used legacy avrae_commands.",
        ))

        missing_files, dispatch_violations = self._scan_for_markers(
            files=CANONICAL_COMBAT_FILES,
            markers=FORBIDDEN_AUTO_DISPATCH_MARKERS,
        )
        checks.append(AggregateSmokeCheck(
            name="canonical_files_present",
            ok=not missing_files,
            message="All canonical combat files are present." if not missing_files else "Some canonical combat files are missing.",
            details={"missing_files": missing_files},
        ))
        checks.append(AggregateSmokeCheck(
            name="no_auto_avrae_dispatch_markers",
            ok=not dispatch_violations,
            message="No Avrae auto-dispatch markers found in canonical combat path." if not dispatch_violations else "Forbidden Avrae auto-dispatch markers found.",
            details={"violations": dispatch_violations},
        ))

        _, legacy_violations = self._scan_for_markers(
            files=("services/combat_event_handler.py", "services/damage_event_handler.py"),
            markers=LEGACY_AVRAE_COMMAND_MARKERS,
        )
        checks.append(AggregateSmokeCheck(
            name="no_legacy_avrae_command_event_producers",
            ok=not legacy_violations,
            message="No legacy type=avrae_command producers found in combat event handlers." if not legacy_violations else "Legacy type=avrae_command producer found.",
            details={"violations": legacy_violations},
        ))

        suggested_contract_ok = self._file_contains("core/turn_output.py", "suggested_commands") and self._file_contains("core/turn_output.py", "dm_instructions")
        checks.append(AggregateSmokeCheck(
            name="turn_output_advisory_contract_present",
            ok=suggested_contract_ok,
            message="TurnOutput advisory fields are present." if suggested_contract_ok else "TurnOutput advisory fields are missing.",
        ))

        ok = all(check.ok for check in checks)
        return AggregateSmokeGateResult(ok=ok, checks=checks, smoke_result=smoke.to_dict())

    def _file_contains(self, rel_path: str, marker: str) -> bool:
        path = self.project_root / rel_path
        return path.exists() and marker in path.read_text(encoding="utf-8")

    def _scan_for_markers(self, files: Iterable[str], markers: Iterable[str]) -> Tuple[List[str], List[Dict[str, str]]]:
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
