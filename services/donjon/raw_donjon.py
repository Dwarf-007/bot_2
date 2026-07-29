"""
SERVICES/DONJON/RAW_DONJON.PY
Centralized extraction of the Donjon-specific raw payload from a room.

Rooms imported from Donjon carry their original export data under
``room["raw"]["donjon"]``. Previously this lookup was re-implemented in several
``services/visibility/*`` modules. This helper removes that duplication.
"""

from __future__ import annotations

from typing import Any, Dict


def extract_donjon_raw(room: Any) -> Dict[str, Any]:
    """Return the Donjon raw payload embedded in a room's ``raw`` field.

    Args:
        room: A room dict (from room_data.json) or any object exposing ``raw``.

    Returns:
        The ``raw["donjon"]`` dict when present, otherwise an empty dict.
    """
    raw = room.get("raw") if isinstance(room, dict) else getattr(room, "raw", None)
    raw = raw or {}
    if not isinstance(raw, dict):
        return {}
    donjon = raw.get("donjon")
    if isinstance(donjon, dict):
        return donjon
    return {}