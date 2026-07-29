
"""
SERVICES/DUNGEON_RUNTIME_GREEN_PATH_SMOKE_SERVICE.PY

Sprint 12.5 update:
- Treats "Nincs látható cella a térkép rendereléséhez." as a semantic map failure.
- This closes the gap where the green-path smoke could pass despite local map not rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional

from services.dungeon_runtime_smoke_diagnostics import DungeonRuntimeSmokeDiagnostics


@dataclass(frozen=True)
class DungeonRuntimeGreenPathCommand:
    name: str
    text: str
    description: str = ""
    forbidden_markers: tuple[str, ...] = ()


@dataclass
class DungeonRuntimeGreenPathStepResult:
    name: str
    text: str
    ok: bool
    public_narrative: str
    error: Optional[str] = None
    detected_issue: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DungeonRuntimeGreenPathSmokeResult:
    ok: bool
    channel_id: str
    player_id: str
    steps: List[DungeonRuntimeGreenPathStepResult] = field(default_factory=list)
    false_green: bool = False
    blocking_failures: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "channel_id": self.channel_id,
            "player_id": self.player_id,
            "false_green": self.false_green,
            "blocking_failures": self.blocking_failures,
            "steps": [step.to_dict() for step in self.steps],
        }

    def summary_text(self) -> str:
        passed = sum(1 for step in self.steps if step.ok)
        total = len(self.steps)
        lines = [f"Dungeon Runtime green-path smoke: {passed}/{total} passed", f"false_green={self.false_green}", f"blocking_failures={self.blocking_failures}"]
        for step in self.steps:
            lines.append(f"- {'OK' if step.ok else 'FAIL'} {step.name}: {step.text}")
            if step.detected_issue:
                lines.append(f"  issue: {step.detected_issue}")
            if step.error:
                lines.append(f"  error: {step.error}")
        return "\n".join(lines)


class DungeonRuntimeGreenPathSmokeService:
    DEFAULT_COMMANDS: List[DungeonRuntimeGreenPathCommand] = [
        DungeonRuntimeGreenPathCommand("look", "look", "Initial player-safe look."),
        DungeonRuntimeGreenPathCommand("map", "map", "Local FOW map render.", forbidden_markers=("Nincs látható cella",)),
        DungeonRuntimeGreenPathCommand("move_choice", "tovább 1", "Concrete movement choice.", forbidden_markers=("Több továbbvezető", "Válassz egy sorszámot", "Nem egyértelmű")),
        DungeonRuntimeGreenPathCommand("back_after_move", "vissza", "Backtracking after concrete move.", forbidden_markers=("Nem egyértelmű, merre van vissza", "Nincs előző", "history")),
        DungeonRuntimeGreenPathCommand("full_map", "teljes térkép", "Full/level FOW map render.", forbidden_markers=("Nincs látható cella",)),
        DungeonRuntimeGreenPathCommand("search_secret", "titkos ajtót keresek", "Player-safe secret search."),
    ]

    def __init__(self, game_turn_service: Any) -> None:
        self.game_turn_service = game_turn_service
        self.diagnostics = DungeonRuntimeSmokeDiagnostics()

    def run(self, *, channel_id: str, player_id: str, campaign_id_override: Optional[str] = None, commands: Optional[Iterable[DungeonRuntimeGreenPathCommand]] = None) -> DungeonRuntimeGreenPathSmokeResult:
        steps = [self._run_one(channel_id=channel_id, player_id=player_id, command=command, campaign_id_override=campaign_id_override) for command in list(commands or self.DEFAULT_COMMANDS)]
        smoke_like = {
            "ok": all(step.ok for step in steps),
            "campaign_id": campaign_id_override or "",
            "channel_id": channel_id,
            "player_id": player_id,
            "bundle_available": True,
            "visibility_available": True,
            "smoke_result": {"ok": all(step.ok for step in steps), "channel_id": channel_id, "player_id": player_id, "steps": [{"name": s.name, "text": s.text, "ok": s.ok, "public_narrative": s.public_narrative, "expected_substring": None} for s in steps]},
        }
        diagnosis = self.diagnostics.diagnose(smoke_like)
        ok = all(step.ok for step in steps) and diagnosis.blocking_failures == 0 and not diagnosis.false_green
        return DungeonRuntimeGreenPathSmokeResult(ok=ok, channel_id=str(channel_id), player_id=str(player_id), steps=steps, false_green=bool(diagnosis.false_green), blocking_failures=int(diagnosis.blocking_failures))

    def _run_one(self, *, channel_id: str, player_id: str, command: DungeonRuntimeGreenPathCommand, campaign_id_override: Optional[str]) -> DungeonRuntimeGreenPathStepResult:
        try:
            try:
                output = self.game_turn_service.process(str(channel_id), str(player_id), command.text, campaign_id_override=campaign_id_override)
            except TypeError:
                output = self.game_turn_service.process(str(channel_id), str(player_id), command.text)
            public_narrative = str(getattr(output, "public_narrative", "") or "")
            ok, issue = self._validate_narrative(public_narrative, command)
            return DungeonRuntimeGreenPathStepResult(command.name, command.text, ok, public_narrative, detected_issue=issue)
        except Exception as exc:
            return DungeonRuntimeGreenPathStepResult(command.name, command.text, False, "", error=str(exc), detected_issue="Exception while processing command.")

    def _validate_narrative(self, narrative: str, command: DungeonRuntimeGreenPathCommand) -> tuple[bool, str]:
        text = str(narrative or "")
        if not text.strip():
            return False, "Empty output."
        low = text.casefold()
        runtime_marker = self.diagnostics._first_marker(low, self.diagnostics.RUNTIME_ERROR_MARKERS)
        if runtime_marker:
            return False, f"Runtime error marker found: {runtime_marker}"
        fallback_marker = self.diagnostics._first_marker(low, self.diagnostics.LLM_FALLBACK_MARKERS)
        if fallback_marker:
            return False, f"LLM fallback marker found: {fallback_marker}"
        for marker in command.forbidden_markers:
            if marker.casefold() in low:
                return False, f"Forbidden green-path marker found: {marker}"
        return True, ""
