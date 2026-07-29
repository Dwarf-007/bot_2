"""
SUBSCRIBERS/COMBAT_RESOLUTION_SUBSCRIBER.PY
Awards XP and sends a short public message when tracked combat ends.
"""

from __future__ import annotations

from core.game_events import EventTypes, GameEvent


class CombatResolutionSubscriber:
    def __init__(self, bot, party_repo, player_repo) -> None:
        self.bot = bot
        self.party_repo = party_repo
        self.player_repo = player_repo

    async def on_all_monsters_defeated_async(self, event: GameEvent) -> None:
        payload = event.payload
        channel_id = str(payload.get("channel_id"))
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return

        party = self.party_repo.get_party_members(channel_id)
        if not party:
            await channel.send("A harc véget ért, de nincs regisztrált party az XP kiosztáshoz.")
            return

        total_xp = int(payload.get("xp_reward_total") or 0)
        if total_xp <= 0:
            await channel.send("A harc véget ért.")
            return

        xp_each = total_xp // max(1, len(party))
        for player_id in party:
            self.player_repo.add_xp(channel_id, player_id, xp_each)

        await channel.send(f"A harc véget ért. XP kiosztva: {xp_each}/fő.")
