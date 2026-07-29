
"""
ENCOUNTER_POLICY.PY - Deterministic encounter difficulty policy.

This module contains pure policy rules. It makes no external calls and is safe
for isolated unit testing.
"""

from typing import Optional


VALID_DIFFICULTIES = {"EASY", "STANDARD", "HARD", "DEADLY"}


def determine_difficulty(
    party_level: int,
    player_count: int,
    scaling_enabled: bool,
    encounter_type: str,
    room_danger_rating: Optional[int] = None,
) -> str:
    """
    Resolves the target difficulty tier for an encounter.

    Args:
        party_level: Average effective party level for the channel.
        player_count: Number of active players.
        scaling_enabled: Campaign-level scaling toggle.
        encounter_type: Encounter category (REST_AMBUSH, STATIC_ROOM, etc.).
        room_danger_rating: Optional local danger modifier.

    Returns:
        One of: EASY, STANDARD, HARD, DEADLY.
    """
    normalized_type = (encounter_type or "STATIC_ROOM").upper()

    safe_party_level = max(1, int(party_level or 1))
    safe_player_count = max(1, int(player_count or 1))
    local_danger = max(0, int(room_danger_rating or 0))
    encounter_budget = safe_party_level * safe_player_count + local_danger

    if not scaling_enabled:
        if normalized_type == "REST_AMBUSH" and encounter_budget <= 4:
            return "EASY"
        return "STANDARD"

    if normalized_type == "REST_AMBUSH":
        if encounter_budget <= 4:
            return "EASY"
        if encounter_budget <= 10:
            return "STANDARD"
        if encounter_budget <= 18:
            return "HARD"
        return "DEADLY"

    if normalized_type == "STATIC_ROOM":
        if encounter_budget <= 4:
            return "STANDARD"
        if encounter_budget <= 10:
            return "HARD"
        return "DEADLY"

    if encounter_budget <= 4:
        return "EASY"
    if encounter_budget <= 10:
        return "STANDARD"
    if encounter_budget <= 18:
        return "HARD"
    return "DEADLY"
