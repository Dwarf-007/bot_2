"""
CORE/TURN_OUTPUT.PY
Canonical output object returned by the game turn pipeline.

C3.1 update:
- Adds DM-facing advisory output fields:
  - dm_instructions
  - suggested_commands
- Avrae commands are kept for backward compatibility, but must be treated as
  advisory/copy-paste suggestions, not as automatically dispatched commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from core.llm_response import SecretMessage


@dataclass
class TurnOutput:
    """
    Final application-level output after deterministic processing.

    Discord layer should send:
    - public_narrative to the channel
    - dm_instructions as DM-facing guidance when present
    - suggested_commands as copy/paste command suggestions when present
    - avrae_commands as legacy/advisory command suggestions when present
    - secret_messages via DM

    C3 boundary rule:
    suggested_commands and avrae_commands must not be automatically dispatched
    by the CombatRuntime. They are advisory output for the DM.
    """

    public_narrative: str = ""
    avrae_commands: List[str] = field(default_factory=list)
    secret_messages: List[SecretMessage] = field(default_factory=list)
    debug_notes: List[str] = field(default_factory=list)
    state_changed: bool = False
    next_room_id: str | None = None
    room_info: dict | None = None

    # C3.1 DM-facing advisory output.
    dm_instructions: List[str] = field(default_factory=list)
    suggested_commands: List[str] = field(default_factory=list)

    def has_dm_guidance(self) -> bool:
        """Return True when there is any DM-facing advisory output."""
        return bool(self.dm_instructions or self.suggested_commands or self.avrae_commands)

    def all_suggested_commands(self) -> List[str]:
        """
        Return all suggestion-style command strings.

        This keeps older avrae_commands readable while C3 migrates callers to
        suggested_commands. Duplicates are removed while preserving order.
        """
        result: List[str] = []
        seen = set()
        for command in [*self.suggested_commands, *self.avrae_commands]:
            normalized = str(command or "").strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result
