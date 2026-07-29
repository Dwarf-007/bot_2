
"""
PARTY_SERVICE.PY

High-level party logic.
"""

from typing import List


class PartyService:

    def __init__(self, party_repo):
        self.party_repo = party_repo

    def get_active_party(self, channel_id: str) -> List[str]:
        return self.party_repo.get_party_members(channel_id)

    def ensure_player_in_party(self, channel_id: str, player_id: str):
        self.party_repo.add_player(channel_id, player_id)
