from __future__ import annotations

import re
from typing import Any, Dict, List


class VisibilityRuntimeFormatter:
    """Player-safe formatter for room and corridor visibility payloads."""

    TARGET_ARROW_RE = re.compile(r"\s*→\s*[^\s]+")
    ROOM_ID_RE = re.compile(r"\b[a-zA-Z0-9_-]+:L\d{2}:R\d{3}\b")
    SEGMENT_ID_RE = re.compile(r"\b[a-zA-Z0-9_-]+:L\d{2}:[A-Z]{2}\d+\b")

    DIRECTION_LABELS = {
        "north": "északi", "south": "déli", "east": "keleti", "west": "nyugati",
        "up": "felfelé vezető", "down": "lefelé vezető",
    }

    def format_look(self, result: Dict[str, Any]) -> str:
        look = result.get("look") if isinstance(result.get("look"), dict) else result
        if not isinstance(look, dict):
            return "Nem látsz egyértelmű kijáratot innen."
        position = look.get("position") or {}
        if isinstance(position, dict) and position.get("node_type") == "segment":
            return self._format_segment_look(look)
        return self._format_room_look(look)

    def _format_room_look(self, look: Dict[str, Any]) -> str:
        description = str(look.get("description") or "").strip()
        exits = look.get("visible_exits") or []
        lines: List[str] = []
        if description:
            lines.append(description)
        if exits:
            lines.append("")
            lines.append("**Látható kijáratok / irányok:**")
            for idx, item in enumerate(exits, start=1):
                label = self._exit_label(item, idx=idx)
                if label:
                    lines.append(f"{idx}. {label}")
        else:
            lines.append("Nem látsz egyértelmű kijáratot innen.")
        return "\n".join(lines).strip()

    def _format_segment_look(self, look: Dict[str, Any]) -> str:
        segment = look.get("segment") or {}
        direction = segment.get("direction_hint") if isinstance(segment, dict) else None
        segment_type = str(segment.get("segment_type") or "corridor_segment") if isinstance(segment, dict) else "corridor_segment"
        connected = [str(x) for x in (segment.get("connected_segments") or [])] if isinstance(segment, dict) else []
        nearby_rooms = [str(x) for x in (look.get("nearby_rooms") or [])]
        visible_segments = [str(x) for x in (look.get("visible_segments") or [])]
        current_segment_id = (look.get("position") or {}).get("segment_id") or (look.get("position") or {}).get("node_id")

        direction_text = self.DIRECTION_LABELS.get(str(direction or "").lower())
        if segment_type == "doorway":
            first = "Egy ajtó vagy átjáró közelében álltok."
        elif direction_text:
            first = f"Egy {direction_text} folyosószakaszon álltok."
        else:
            first = "Egy folyosószakaszon álltok."

        lines: List[str] = [first]
        lines.append("A látható szakasz a következő kanyarig vagy csatlakozásig követhető; azon túl nem láttok tovább.")

        next_segments: List[str] = []
        for sid in connected or visible_segments:
            if current_segment_id and sid == current_segment_id:
                continue
            if sid not in next_segments:
                next_segments.append(sid)

        options: List[str] = []
        for idx, _sid in enumerate(next_segments, start=1):
            options.append(self._corridor_option_label(idx, len(next_segments), bool(direction_text), direction_text))
        if nearby_rooms:
            options.append("Vissza vagy be egy közeli ismert helyiség bejáratához")

        if options:
            lines.append("")
            lines.append("**Látható továbbhaladás:**")
            for idx, label in enumerate(options, start=1):
                lines.append(f"{idx}. {label}")
        else:
            lines.append("")
            lines.append("Nem látsz egyértelmű továbbhaladási lehetőséget innen.")

        count = look.get("visible_cells_count")
        if count:
            lines.append("")
            lines.append(f"_Látható térképrészlet: {count} cella._")
        return "\n".join(lines).strip()

    def _corridor_option_label(self, idx: int, total: int, has_direction: bool, direction_text: str | None) -> str:
        if idx == 1:
            if has_direction and direction_text:
                return f"Tovább a {direction_text} folyosószakasz irányába"
            return "Tovább a folyosón"
        if idx == 2:
            return "Vissza vagy oldalág felé"
        return "Másik folyosóág felé"

    def format_move(self, result: Dict[str, Any]) -> str:
        if not result.get("ok"):
            msg = str(result.get("message") or "Nem sikerült a mozgás.")
            msg = msg.replace("Adj meg --choice N értéket.", "Válassz egy sorszámot, például: `tovább 1` vagy `megyünk keletre 1`.")
            msg = msg.replace("például: `megyünk keletre 3`", "például: `tovább 1` vagy `megyünk keletre 1`")
            ambiguity = result.get("ambiguity") or []
            if ambiguity:
                lines = [self._sanitize_label(msg), "", "**Választható lehetőségek:**"]
                for idx, item in enumerate(ambiguity, start=1):
                    lines.append(f"{idx}. {self._exit_label(item, idx=idx, total=len(ambiguity))}")
                return "\n".join(lines)
            return self._sanitize_label(msg)

        msg = self._friendly_move_message(str(result.get("message") or "Mozgás sikeres."))
        look = result.get("look")
        if isinstance(look, dict):
            formatted = self.format_look({"look": look})
            if formatted:
                return f"{msg}\n\n{formatted}"
        return msg

    def _friendly_move_message(self, msg: str) -> str:
        low = msg.lower()
        if "folyosószakasz" in low or self.SEGMENT_ID_RE.search(msg):
            return "Továbbhaladtok a folyosón."
        return self._sanitize_label(msg)

    def format_secret_search(self, result: Dict[str, Any]) -> str:
        if result.get("found") or result.get("revealed") or result.get("success"):
            return str(result.get("message") or "Találtatok valami szokatlant: egy rejtett részlet felfedhetővé vált.")
        return str(result.get("message") or "Alapos vizsgálat után sem találtok rejtett ajtót.")

    def _exit_label(self, item: Any, idx: int = 1, total: int = 1) -> str:
        if not isinstance(item, dict):
            cleaned = self._sanitize_label(str(item))
            if cleaned == "folyosószakasz":
                return self._corridor_option_label(idx, total, False, None)
            return cleaned
        label = item.get("label") or item.get("player_label") or item.get("description") or item.get("segment_id") or item.get("direction")
        cleaned = self._sanitize_label(str(label or "ismeretlen kijárat"))
        if cleaned == "folyosószakasz" or cleaned.startswith("folyosószakasz"):
            direction = item.get("direction_hint")
            direction_text = self.DIRECTION_LABELS.get(str(direction or "").lower())
            return self._corridor_option_label(idx, total, bool(direction_text), direction_text)
        return cleaned

    def _sanitize_label(self, text: str) -> str:
        cleaned = self.TARGET_ARROW_RE.sub("", str(text or ""))
        cleaned = self.ROOM_ID_RE.sub("", cleaned)
        cleaned = self.SEGMENT_ID_RE.sub("folyosószakasz", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = cleaned.strip(" -–—:")
        return cleaned.strip()
