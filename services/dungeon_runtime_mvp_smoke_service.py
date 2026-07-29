"""
SERVICES/DUNGEON_RUNTIME_MVP_SMOKE_SERVICE.PY
Sprint 11.6 update: pass campaign_id_override through GameTurnService.process() when provided.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional

@dataclass(frozen=True)
class DungeonRuntimeMvpSmokeCommand:
    name: str
    text: str
    expected_substring: Optional[str] = None
    description: str = ""

@dataclass
class DungeonRuntimeMvpSmokeStepResult:
    name: str
    text: str
    ok: bool
    public_narrative: str
    expected_substring: Optional[str] = None
    error: Optional[str] = None
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class DungeonRuntimeMvpSmokeResult:
    ok: bool
    channel_id: str
    player_id: str
    steps: List[DungeonRuntimeMvpSmokeStepResult] = field(default_factory=list)
    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "channel_id": self.channel_id, "player_id": self.player_id, "steps": [s.to_dict() for s in self.steps]}
    def summary_text(self) -> str:
        passed = sum(1 for s in self.steps if s.ok)
        lines = [f"Dungeon Runtime MVP smoke: {passed}/{len(self.steps)} passed"]
        for s in self.steps:
            lines.append(f"- {'OK' if s.ok else 'FAIL'} {s.name}: {s.text}")
            if s.error:
                lines.append(f"  error: {s.error}")
        return "\n".join(lines)

class DungeonRuntimeMvpSmokeService:
    DEFAULT_COMMANDS: List[DungeonRuntimeMvpSmokeCommand] = [
        DungeonRuntimeMvpSmokeCommand("look", "look", expected_substring=None),
        DungeonRuntimeMvpSmokeCommand("map", "map", expected_substring=None),
        DungeonRuntimeMvpSmokeCommand("move", "megyek északra", expected_substring=None),
        DungeonRuntimeMvpSmokeCommand("back", "vissza", expected_substring=None),
        DungeonRuntimeMvpSmokeCommand("search_secret", "titkos ajtót keresek", expected_substring=None),
        DungeonRuntimeMvpSmokeCommand("full_map", "teljes térkép", expected_substring=None),
    ]
    def __init__(self, game_turn_service: Any) -> None:
        self.game_turn_service = game_turn_service
    def run(self, *, channel_id: str, player_id: str, campaign_id_override: Optional[str] = None, commands: Optional[Iterable[DungeonRuntimeMvpSmokeCommand]] = None) -> DungeonRuntimeMvpSmokeResult:
        steps = [self._run_one(channel_id=channel_id, player_id=player_id, command=c, campaign_id_override=campaign_id_override) for c in list(commands or self.DEFAULT_COMMANDS)]
        return DungeonRuntimeMvpSmokeResult(ok=all(s.ok for s in steps), channel_id=str(channel_id), player_id=str(player_id), steps=steps)
    def _run_one(self, *, channel_id: str, player_id: str, command: DungeonRuntimeMvpSmokeCommand, campaign_id_override: Optional[str]) -> DungeonRuntimeMvpSmokeStepResult:
        try:
            try:
                output = self.game_turn_service.process(str(channel_id), str(player_id), command.text, campaign_id_override=campaign_id_override)
            except TypeError:
                output = self.game_turn_service.process(str(channel_id), str(player_id), command.text)
            text = str(getattr(output, "public_narrative", "") or "")
            ok = bool(text.strip())
            if command.expected_substring:
                ok = ok and command.expected_substring.casefold() in text.casefold()
            return DungeonRuntimeMvpSmokeStepResult(command.name, command.text, ok, text, command.expected_substring)
        except Exception as exc:
            return DungeonRuntimeMvpSmokeStepResult(command.name, command.text, False, "", command.expected_substring, str(exc))
