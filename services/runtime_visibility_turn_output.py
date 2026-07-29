from __future__ import annotations

import dataclasses
from typing import Any, Dict


def make_turn_output(text: str, *, debug: Dict[str, Any] | None = None):
    """Construct core.turn_output.TurnOutput defensively across refactor versions.

    Hotfix: current project TurnOutput uses `public_narrative`, not
    `public_message`/`narrative`. If this field is not populated,
    GameTurnService._finalize_output replaces the actual visibility output with
    the generic fallback text.
    """
    from core.turn_output import TurnOutput

    debug = debug or {}

    if dataclasses.is_dataclass(TurnOutput):
        field_names = {f.name for f in dataclasses.fields(TurnOutput)}
        kwargs: Dict[str, Any] = {}

        for candidate in (
            "public_narrative",
            "public_message",
            "narrative",
            "text",
            "message",
        ):
            if candidate in field_names:
                kwargs[candidate] = text
                break

        if "avrae_commands" in field_names:
            kwargs["avrae_commands"] = []
        if "secret_messages" in field_names:
            kwargs["secret_messages"] = []
        if "debug_notes" in field_names:
            kwargs["debug_notes"] = []
        if "debug" in field_names:
            kwargs["debug"] = debug
        if "metadata" in field_names:
            kwargs["metadata"] = debug
        if "state_changed" in field_names:
            kwargs["state_changed"] = False
        if "next_room_id" in field_names:
            kwargs["next_room_id"] = None

        try:
            return TurnOutput(**kwargs)
        except TypeError:
            pass

    try:
        return TurnOutput(public_narrative=text)
    except Exception:
        try:
            return TurnOutput(text)
        except Exception:
            return {
                "public_narrative": text,
                "avrae_commands": [],
                "secret_messages": [],
                "debug": debug,
            }
