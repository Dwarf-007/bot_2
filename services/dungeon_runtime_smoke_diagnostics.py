"""
SERVICES/DUNGEON_RUNTIME_SMOKE_DIAGNOSTICS.PY

Sprint 12.1 - Smoke Result Diagnostics + False Green Detection.

Purpose:
- Diagnose Dungeon Runtime MVP smoke result JSON files.
- Detect "false green" smoke runs where smoke_result.ok is true but one or more
  steps contain runtime error narratives or fallback outputs.
- Classify ambiguous movement / no-history backtracking as acceptable MVP outcomes
  instead of generic failures.

This module does not fix runtime bugs. It makes the smoke output actionable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class SmokeStepStatus(str, Enum):
    PASS = "PASS"
    FALSE_GREEN_RUNTIME_ERROR = "FALSE_GREEN_RUNTIME_ERROR"
    FALSE_GREEN_LLM_FALLBACK = "FALSE_GREEN_LLM_FALLBACK"
    OK_AMBIGUOUS_CHOICE = "OK_AMBIGUOUS_CHOICE"
    OK_NO_BACK_HISTORY = "OK_NO_BACK_HISTORY"
    FAIL_EMPTY_OUTPUT = "FAIL_EMPTY_OUTPUT"
    FAIL_EXPECTATION_MISMATCH = "FAIL_EXPECTATION_MISMATCH"
    FAIL_STEP_MARKED_FAILED = "FAIL_STEP_MARKED_FAILED"
    WARN_UNCLASSIFIED = "WARN_UNCLASSIFIED"


@dataclass(frozen=True)
class SmokeStepDiagnosis:
    name: str
    text: str
    status: SmokeStepStatus
    ok_flag: bool
    public_narrative: str
    expected_substring: Optional[str] = None
    detected_issue: str = ""
    recommendation: str = ""

    @property
    def is_blocking_failure(self) -> bool:
        return self.status in {
            SmokeStepStatus.FALSE_GREEN_RUNTIME_ERROR,
            SmokeStepStatus.FALSE_GREEN_LLM_FALLBACK,
            SmokeStepStatus.FAIL_EMPTY_OUTPUT,
            SmokeStepStatus.FAIL_EXPECTATION_MISMATCH,
            SmokeStepStatus.FAIL_STEP_MARKED_FAILED,
        }

    @property
    def is_false_green(self) -> bool:
        return self.status in {
            SmokeStepStatus.FALSE_GREEN_RUNTIME_ERROR,
            SmokeStepStatus.FALSE_GREEN_LLM_FALLBACK,
        }

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["is_blocking_failure"] = self.is_blocking_failure
        data["is_false_green"] = self.is_false_green
        return data


@dataclass
class SmokeRunDiagnosis:
    ok: bool
    false_green: bool
    original_ok: bool
    campaign_id: str
    channel_id: str
    player_id: str
    bundle_available: bool
    visibility_available: bool
    campaign_forced: bool = False
    channel_bound: bool = False
    blocking_failures: int = 0
    false_green_steps: int = 0
    warnings: List[str] = field(default_factory=list)
    steps: List[SmokeStepDiagnosis] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "false_green": self.false_green,
            "original_ok": self.original_ok,
            "campaign_id": self.campaign_id,
            "channel_id": self.channel_id,
            "player_id": self.player_id,
            "bundle_available": self.bundle_available,
            "visibility_available": self.visibility_available,
            "campaign_forced": self.campaign_forced,
            "channel_bound": self.channel_bound,
            "blocking_failures": self.blocking_failures,
            "false_green_steps": self.false_green_steps,
            "warnings": list(self.warnings),
            "steps": [step.to_dict() for step in self.steps],
        }

    def summary_text(self) -> str:
        lines = [
            f"Dungeon Runtime smoke diagnosis: {'OK' if self.ok else 'FAIL'}",
            f"original_ok={self.original_ok}",
            f"false_green={self.false_green}",
            f"campaign_id={self.campaign_id}",
            f"channel_id={self.channel_id}",
            f"bundle_available={self.bundle_available}",
            f"visibility_available={self.visibility_available}",
            f"blocking_failures={self.blocking_failures}",
            f"false_green_steps={self.false_green_steps}",
        ]
        if self.warnings:
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"- {warning}")
        lines.append("Steps:")
        for step in self.steps:
            marker = "OK" if not step.is_blocking_failure else "FAIL"
            lines.append(f"- {marker} {step.name}: {step.status.value}")
            if step.detected_issue:
                lines.append(f"  issue: {step.detected_issue}")
            if step.recommendation:
                lines.append(f"  next: {step.recommendation}")
        return "\n".join(lines)


class DungeonRuntimeSmokeDiagnostics:
    """Classifier for Dungeon Runtime MVP smoke JSON outputs."""

    RUNTIME_ERROR_MARKERS = (
        "A visibility runtime hibát jelzett:",
        "visibility runtime hibát jelzett",
        "runtime error",
        "Traceback",
        "SyntaxError",
        "unterminated string literal",
    )
    LLM_FALLBACK_MARKERS = (
        "A narrációs modell jelenleg nem válaszol megbízhatóan",
        "narrációs modell jelenleg nem válaszol",
        "LLM",
    )
    AMBIGUITY_MARKERS = (
        "Több továbbvezető",
        "Több látható",
        "Válassz egy sorszámot",
        "Adj meg",
        "choice",
        "választás",
    )
    NO_BACK_HISTORY_MARKERS = (
        "Nem egyértelmű, merre van vissza",
        "Nincs előző",
        "nincs vissza",
        "history",
    )

    def diagnose_file(self, path: str | Path) -> SmokeRunDiagnosis:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return self.diagnose(data)

    def diagnose(self, data: Dict[str, Any]) -> SmokeRunDiagnosis:
        smoke_result = data.get("smoke_result") or {}
        steps_raw = smoke_result.get("steps") or []
        steps = [self.diagnose_step(step) for step in steps_raw if isinstance(step, dict)]
        blocking = sum(1 for step in steps if step.is_blocking_failure)
        false_green_steps = sum(1 for step in steps if step.is_false_green)
        original_ok = bool(data.get("ok") and smoke_result.get("ok", True))
        warnings: List[str] = []
        if original_ok and false_green_steps:
            warnings.append("Smoke result reports ok=true, but runtime/fallback error narratives were detected.")
        if bool(data.get("bundle_available")) is False:
            warnings.append("Bundle was not available; smoke did not reach Dungeon Runtime.")
        if bool(data.get("visibility_available")) is False:
            warnings.append("Visibility runtime was not available for this bundle.")
        if not steps:
            warnings.append("No smoke steps were found in smoke_result.steps.")

        return SmokeRunDiagnosis(
            ok=(blocking == 0 and bool(data.get("bundle_available")) and bool(data.get("visibility_available"))),
            false_green=(original_ok and false_green_steps > 0),
            original_ok=original_ok,
            campaign_id=str(data.get("campaign_id") or ""),
            channel_id=str(data.get("channel_id") or smoke_result.get("channel_id") or ""),
            player_id=str(data.get("player_id") or smoke_result.get("player_id") or ""),
            bundle_available=bool(data.get("bundle_available", False)),
            visibility_available=bool(data.get("visibility_available", False)),
            campaign_forced=bool(data.get("campaign_forced", False)),
            channel_bound=bool(data.get("channel_bound", False)),
            blocking_failures=blocking,
            false_green_steps=false_green_steps,
            warnings=warnings,
            steps=steps,
        )

    def diagnose_step(self, step: Dict[str, Any]) -> SmokeStepDiagnosis:
        name = str(step.get("name") or "")
        text = str(step.get("text") or "")
        narrative = str(step.get("public_narrative") or "")
        ok_flag = bool(step.get("ok", False))
        expected = step.get("expected_substring")
        expected_s = str(expected) if expected is not None else None
        low = narrative.casefold()

        if not narrative.strip():
            return self._diag(step, SmokeStepStatus.FAIL_EMPTY_OUTPUT, "No public_narrative was produced.", "Check handler return path and TurnOutput construction.")

        runtime_marker = self._first_marker(low, self.RUNTIME_ERROR_MARKERS)
        if runtime_marker:
            return self._diag(step, SmokeStepStatus.FALSE_GREEN_RUNTIME_ERROR, f"Runtime error marker found: {runtime_marker}", self._runtime_recommendation(name, narrative))

        llm_marker = self._first_marker(low, self.LLM_FALLBACK_MARKERS)
        if llm_marker:
            return self._diag(step, SmokeStepStatus.FALSE_GREEN_LLM_FALLBACK, f"LLM fallback marker found: {llm_marker}", "Verify RuntimeModeRouter routed this command to Dungeon Runtime and campaign override/channel binding are active.")

        if name in {"move", "movement"} and self._contains_any(low, self.AMBIGUITY_MARKERS):
            return self._diag(step, SmokeStepStatus.OK_AMBIGUOUS_CHOICE, "Movement produced a valid ambiguity/choice prompt.", "For green-path smoke, rerun with a concrete choice such as 'tovább 1' or 'megyek keletre 1'.")

        if name in {"back", "backtrack"} and self._contains_any(low, self.NO_BACK_HISTORY_MARKERS):
            return self._diag(step, SmokeStepStatus.OK_NO_BACK_HISTORY, "Backtracking reports no clear previous route/history yet.", "This is acceptable immediately after reset; validate back after a successful move.")

        if expected_s and expected_s.casefold() not in low:
            return self._diag(step, SmokeStepStatus.FAIL_EXPECTATION_MISMATCH, f"Expected substring not found: {expected_s}", "Adjust expected substring or fix formatter output.")

        if not ok_flag:
            return self._diag(step, SmokeStepStatus.FAIL_STEP_MARKED_FAILED, "Step ok flag is false.", "Inspect raw step output and corresponding command handler.")

        return self._diag(step, SmokeStepStatus.PASS, "Step output looks acceptable.", "")

    def _diag(self, step: Dict[str, Any], status: SmokeStepStatus, issue: str, recommendation: str) -> SmokeStepDiagnosis:
        return SmokeStepDiagnosis(
            name=str(step.get("name") or ""),
            text=str(step.get("text") or ""),
            status=status,
            ok_flag=bool(step.get("ok", False)),
            public_narrative=str(step.get("public_narrative") or ""),
            expected_substring=str(step.get("expected_substring")) if step.get("expected_substring") is not None else None,
            detected_issue=issue,
            recommendation=recommendation,
        )

    @staticmethod
    def _contains_any(text: str, markers: Iterable[str]) -> bool:
        low = text.casefold()
        return any(str(marker).casefold() in low for marker in markers)

    @staticmethod
    def _first_marker(text: str, markers: Iterable[str]) -> Optional[str]:
        low = text.casefold()
        for marker in markers:
            marker_s = str(marker)
            if marker_s.casefold() in low:
                return marker_s
        return None

    @staticmethod
    def _runtime_recommendation(step_name: str, narrative: str) -> str:
        low = narrative.casefold()
        if "runtime_visibility_map_service.py" in low or "unterminated string literal" in low:
            return "Fix runtime_visibility_map_service.py syntax/string escaping; affects map/full_map commands."
        if "secretdiscoverystatestore" in low or "secretdiscoverystatestore" in low:
            return "Fix SecretDoorDiscoveryEngine construction in RuntimeVisibilityCommandHandler.search_secret()."
        return f"Inspect the {step_name} command handler and raw exception path."
