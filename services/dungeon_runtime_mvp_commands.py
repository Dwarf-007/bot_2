"""
SERVICES/DUNGEON_RUNTIME_MVP_COMMANDS.PY

Sprint 11.2 - Dungeon Runtime MVP command catalog.

Purpose:
- Define the first playable Dungeon Mode command surface.
- Keep dungeon runtime routing deterministic and player-safe.
- Avoid sending arbitrary campaign/sandbox chatter into Dungeon Runtime.

MVP command families:
- LOOK
- MOVE
- BACK, represented as MOVE(direction="back")
- MAP, local or full
- SEARCH_SECRET
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from services.runtime_visibility_intents import RuntimeVisibilityIntent, RuntimeVisibilityIntentParser


@dataclass(frozen=True)
class DungeonRuntimeCommandSpec:
    kind: str
    examples: List[str]
    description: str
    player_safe: bool = True


class DungeonRuntimeMvpCommandCatalog:
    """Defines and validates the Dungeon Runtime MVP command surface."""

    DUNGEON_MVP_INTENTS: Set[str] = {"LOOK", "MOVE", "MAP", "SEARCH_SECRET"}

    def __init__(self, parser: Optional[RuntimeVisibilityIntentParser] = None) -> None:
        self.parser = parser or RuntimeVisibilityIntentParser()

    def parse(self, text: str) -> RuntimeVisibilityIntent:
        return self.parser.parse(text)

    def is_mvp_intent(self, intent: RuntimeVisibilityIntent) -> bool:
        return bool(intent and intent.kind in self.DUNGEON_MVP_INTENTS)

    def is_mvp_command(self, text: str) -> bool:
        return self.is_mvp_intent(self.parse(text))

    def specs(self) -> List[DungeonRuntimeCommandSpec]:
        return [
            DungeonRuntimeCommandSpec(
                kind="LOOK",
                examples=["look", "körülnézek", "mit látok?", "merre lehet menni?"],
                description="Refreshes the current player-safe look output and visible exits.",
            ),
            DungeonRuntimeCommandSpec(
                kind="MOVE",
                examples=["north", "megyek északra", "move east", "2", "vissza"],
                description="Moves into a visible segment/room choice, or backtracks with back/vissza.",
            ),
            DungeonRuntimeCommandSpec(
                kind="MAP",
                examples=["map", "térkép", "local map", "teljes térkép", "full map"],
                description="Renders local or full 3-state fog-of-war map output.",
            ),
            DungeonRuntimeCommandSpec(
                kind="SEARCH_SECRET",
                examples=["titkos ajtót keresek", "rejtett ajtót keresek", "search secret door"],
                description="Runs player-safe secret door discovery for the current room context.",
            ),
        ]

    def help_text(self) -> str:
        lines = ["Dungeon mód parancsok:"]
        for spec in self.specs():
            examples = ", ".join(f"`{x}`" for x in spec.examples[:4])
            lines.append(f"- {spec.kind}: {spec.description} Példák: {examples}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, object]:
        return {
            "mvp_intents": sorted(self.DUNGEON_MVP_INTENTS),
            "commands": [
                {
                    "kind": spec.kind,
                    "examples": list(spec.examples),
                    "description": spec.description,
                    "player_safe": spec.player_safe,
                }
                for spec in self.specs()
            ],
        }
