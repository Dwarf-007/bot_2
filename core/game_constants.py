"""
CORE/GAME_CONSTANTS.PY
Shared, named game-balance defaults.

Centralizes magic values that were previously hardcoded at call sites
(e.g. party_level=1, scaling_enabled=False in encounter preparation).
"""

from __future__ import annotations

# Default party level used when an encounter is prepared without an explicit
# party level (legacy/compatibility path).
DEFAULT_PARTY_LEVEL: int = 1

# Whether prepared encounters should apply automatic difficulty scaling.
DEFAULT_ENCOUNTER_SCALING_ENABLED: bool = False