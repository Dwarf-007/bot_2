from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class PlayerLookSanitizer:
    """Sanitizes visibility look payloads for player-facing output.

    Goals:
    - Remove legacy high-level room-to-room edge entries from player visible_exits.
      These entries often contain raw Donjon text such as "Trapped ..." and expose target rooms.
    - Keep only segment-based exits in player look.
    - Strip target room IDs from player labels/descriptions.
    - Hide DM-only/mechanical fields from player-facing entries by default.

    Runtime/DM data remains available in corridor_visibility_labels.json and door_metadata,
    but it should not be printed to Discord players unless a DM/debug renderer explicitly asks for it.
    """

    TARGET_ARROW_RE = re.compile(r"\s*→\s*[^\s]+")
    TARGET_ROOM_RE = re.compile(r"\b[a-zA-Z0-9_-]+:L\d{2}:R\d{3}\b")
    SPOILER_WORD_RE = re.compile(
        r"\b(trapped|trap|secret|hidden|concealed|invisible)\b",
        flags=re.IGNORECASE,
    )

    DM_ONLY_KEYS = {
        'dm_label',
        'dm_description',
        'door_metadata',
        'hidden_traits',
        'requires_detection',
        'target_room_ids',
    }

    # Keep these for runtime choice handling, but Discord renderer can still ignore them.
    RUNTIME_SAFE_KEYS = {
        'segment_id',
        'segment_type',
        'direction_hint',
        'direction',
        'label',
        'description',
        'player_label',
        'player_description',
        'visible_traits',
        'revealed_traits',
    }

    def sanitize_look(self, look: Dict[str, Any], *, include_dm: bool = False) -> Dict[str, Any]:
        look = dict(look)
        if 'visible_exits' in look:
            look['visible_exits'] = self.sanitize_exits(look.get('visible_exits') or [], include_dm=include_dm)
        return look

    def sanitize_exits(self, exits: List[Dict[str, Any]], *, include_dm: bool = False) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        seen = set()
        for item in exits:
            sanitized = self.sanitize_exit(item, include_dm=include_dm)
            if not sanitized:
                continue
            key = sanitized.get('segment_id') or (sanitized.get('direction'), sanitized.get('label'), sanitized.get('description'))
            if key in seen:
                continue
            seen.add(key)
            result.append(sanitized)
        return result

    def sanitize_exit(self, item: Dict[str, Any], *, include_dm: bool = False) -> Optional[Dict[str, Any]]:
        # Player look should not expose high-level room edge entries from navigation_index.
        # Those entries have room_id but no segment_id and can contain raw spoiler text.
        if not item.get('segment_id'):
            return None

        out = dict(item)

        # Prefer player-safe fields if present.
        if out.get('player_label'):
            out['label'] = out['player_label']
        if out.get('player_description'):
            out['description'] = out['player_description']

        if out.get('label'):
            out['label'] = self.sanitize_text(str(out['label']))
        if out.get('description'):
            out['description'] = self.sanitize_text(str(out['description']))

        # Secret exits are filtered by SecretDoorDiscoveryEngine before/after this layer.
        # This sanitizer is still defensive: if an unrevealed secret item reaches here, hide it.
        hidden_traits = set(out.get('hidden_traits') or [])
        revealed_traits = set(out.get('revealed_traits') or [])
        if 'secret' in hidden_traits and 'secret' not in revealed_traits:
            return None

        if include_dm:
            return out

        # Remove DM-only details from player payload.
        for key in list(out.keys()):
            if key in self.DM_ONLY_KEYS:
                out.pop(key, None)

        # Keep payload compact and player-safe. Unknown extra raw fields are dropped.
        compact = {k: v for k, v in out.items() if k in self.RUNTIME_SAFE_KEYS and v is not None}
        return compact

    def sanitize_text(self, text: str) -> str:
        text = self.TARGET_ARROW_RE.sub('', text)
        text = self.TARGET_ROOM_RE.sub('', text)
        # Do not try to rewrite sentences that contain spoiler words; remove the words only.
        # The door_visibility_policy should already have produced clean player text.
        text = self.SPOILER_WORD_RE.sub('', text)
        text = re.sub(r'\s{2,}', ' ', text).strip()
        text = text.replace(' :', ':').replace(' ,', ',')
        return text
