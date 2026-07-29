from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class DoorVisibilityLabels:
    player_label: str
    player_description: str
    dm_label: str
    dm_description: str
    hidden_traits: List[str]
    visible_traits: List[str]
    requires_detection: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DoorVisibilityPolicy:
    """Player-safe vs DM-only door labeling policy.

    Player labels intentionally do NOT include target room IDs and do NOT reveal hidden traits.
    DM labels may include target room IDs and full hidden traits.
    """

    def build_labels(
        self,
        *,
        direction: Optional[str],
        entry_index: int,
        desc: str,
        door_type: str = '',
        target_room_id: Optional[str] = None,
        trap: Optional[str] = None,
        secret: Optional[Any] = None,
    ) -> DoorVisibilityLabels:
        hidden_traits = self.hidden_traits(desc=desc, door_type=door_type, trap=trap, secret=secret)
        visible_traits = self.visible_traits(desc=desc, door_type=door_type)

        direction_hu = self.direction_label_hu(direction)
        ordinal = f' #{entry_index}' if entry_index > 1 else ''
        dm_target = f' → {target_room_id}' if target_room_id else ''

        player_noun = self.player_safe_noun(desc, door_type, hidden_traits)
        player_prefix_traits = self.player_visible_prefix_traits(visible_traits)
        player_short = ' '.join(player_prefix_traits + [player_noun]).strip()
        # IMPORTANT: no target_room_id in player label.
        player_label = f'{direction_hu} bejárat{ordinal}: {player_short}'
        player_description = self.player_safe_description(direction_hu, player_short, hidden_traits)

        dm_short = self.dm_short_desc_hu(desc, door_type, hidden_traits, visible_traits)
        dm_label = f'{direction_hu} bejárat{ordinal}: {dm_short}{dm_target}'
        dm_description = desc or dm_short
        if trap:
            dm_description += f' | Csapda: {self.first_line(trap)}'
        if secret:
            dm_description += f' | Rejtés: {self.first_line(str(secret))}'

        return DoorVisibilityLabels(
            player_label=player_label,
            player_description=player_description,
            dm_label=dm_label,
            dm_description=dm_description,
            hidden_traits=hidden_traits,
            visible_traits=visible_traits,
            requires_detection=bool(hidden_traits),
        )

    def hidden_traits(self, *, desc: str, door_type: str = '', trap: Optional[str] = None, secret: Optional[Any] = None) -> List[str]:
        low = (desc or '').lower()
        traits: List[str] = []
        if trap or re.search(r'\btrapped\b|\btrap\b', low) or door_type == 'trapped':
            traits.append('trapped')
        if secret or re.search(r'\bsecret\b|\bconcealed\b|\binvisible\b|\bhidden\b', low) or door_type == 'secret':
            traits.append('secret')
        return self._dedupe(traits)

    def visible_traits(self, *, desc: str, door_type: str = '') -> List[str]:
        low = (desc or '').lower()
        traits: List[str] = []
        if re.search(r'(?<!un)\blocked\b', low) or door_type == 'locked':
            traits.append('locked')
        if re.search(r'\bstuck\b', low):
            traits.append('stuck')
        return self._dedupe(traits)

    def player_visible_prefix_traits(self, visible_traits: List[str]) -> List[str]:
        mapping = {'locked': 'zárt', 'stuck': 'beragadt'}
        return [mapping[t] for t in visible_traits if t in mapping]

    def dm_visible_prefix_traits(self, hidden_traits: List[str], visible_traits: List[str]) -> List[str]:
        mapping = {'secret': 'rejtett', 'trapped': 'csapdázott', 'locked': 'zárt', 'stuck': 'beragadt'}
        ordered = ['secret', 'trapped', 'locked', 'stuck']
        traits = set(hidden_traits) | set(visible_traits)
        return [mapping[t] for t in ordered if t in traits and t in mapping]

    def player_safe_noun(self, desc: str, door_type: str = '', hidden_traits: Optional[List[str]] = None) -> str:
        low = (desc or '').lower()
        if 'portcullis' in low:
            return 'rostélykapu'
        if 'archway' in low or door_type == 'arch':
            return 'boltíves átjáró'
        if 'stone door' in low:
            return 'kőajtó'
        if 'iron door' in low:
            return 'vasajtó'
        if 'wooden door' in low:
            return 'faajtó'
        if 'door' in low:
            return 'ajtó'
        return 'átjáró'

    def dm_short_desc_hu(self, desc: str, door_type: str, hidden_traits: List[str], visible_traits: List[str]) -> str:
        noun = self.player_safe_noun(desc, door_type, hidden_traits)
        prefixes = self.dm_visible_prefix_traits(hidden_traits, visible_traits)
        return ' '.join(prefixes + [noun]) if prefixes else noun

    def player_safe_description(self, direction_hu: str, player_short: str, hidden_traits: List[str]) -> str:
        if 'secret' in hidden_traits:
            return f'{direction_hu} irányban a fal vagy környezet különösebb vizsgálatot igényelhet.'
        return f'{direction_hu} irányban {self._indefinite_article_hu(player_short)} {player_short} látható.'

    @staticmethod
    def direction_label_hu(direction: Optional[str]) -> str:
        return {
            'north': 'Északi', 'south': 'Déli', 'east': 'Keleti', 'west': 'Nyugati',
            'up': 'Felfelé vezető', 'down': 'Lefelé vezető',
            'n': 'Északi', 's': 'Déli', 'e': 'Keleti', 'w': 'Nyugati',
        }.get(str(direction or '').lower(), 'Ismeretlen')

    @staticmethod
    def first_line(text: str) -> str:
        return str(text or '').strip().splitlines()[0] if text else ''

    @staticmethod
    def _indefinite_article_hu(text: str) -> str:
        if not text:
            return 'egy'
        return 'az' if text[0].lower() in 'aáeéiíoóöőuúüű' else 'egy'

    @staticmethod
    def _dedupe(values: List[str]) -> List[str]:
        out: List[str] = []
        for value in values:
            if value not in out:
                out.append(value)
        return out
