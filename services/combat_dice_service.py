"""
SERVICES/COMBAT_DICE_SERVICE.PY
Small dice helper for non-authoritative AI-DM combat advisory calculations.

C4.4 extraction:
- Owns local d20 and damage dice rolling helpers used for narration/advisory output.

Boundary:
- No Discord I/O.
- No Avrae dispatch.
- No LLM calls.
- No combat session lifecycle mutation.
- These rolls are not authoritative when the table uses Avrae.
"""

from __future__ import annotations

import random
import re


class CombatDiceService:
    """Utility service for local advisory dice calculations."""

    def roll_d20_plus(self, bonus: int = 0) -> int:
        return random.randint(1, 20) + int(bonus or 0)

    def roll_damage(self, damage_str: str) -> int:
        """Roll simple dice notation like '1d6+2'. Returns 1 for unsupported input."""
        match = re.match(r"(\d+)d(\d+)([+-]\d+)?", str(damage_str or ""))
        if not match:
            return 1
        num = int(match.group(1))
        sides = int(match.group(2))
        mod = int(match.group(3) or 0)
        return sum(random.randint(1, sides) for _ in range(num)) + mod
