"""
SERVICES/SUBSCRIBERS/DISCORD_SUBSCRIBER.PY

Sends messages to Discord as reactions to events.

Requires:
- discord client injected externally
"""

from __future__ import annotations


class DiscordSubscriber:
    """
    Sends messages to Discord as reactions to events.

    Requires:
    - discord client injected externally
    """

    def __init__(self, bot) -> None:
        self.bot = bot

    async def on_combat_started(self, payload):
        channel = self.bot.get_channel(int(payload["channel_id"]))
        if not channel:
            return
        await channel.send("⛗️ Harc kezdődik!")
