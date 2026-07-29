
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class NarrationInput:
    room_title: str
    room_facts: str

    action_type: str

    exit_reason: Optional[str] = None

    trap_triggered: bool = False
    trap_names: List[str] = field(default_factory=list)

    combat_triggered: bool = False


@dataclass(frozen=True)
class NarrationResult:
    text: str
