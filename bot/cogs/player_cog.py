# bot/cogs/player_cog.py
from __future__ import annotations

import discord
from discord.ext import commands

from services.player_manager import PlayerManager


class PlayerCog(commands.Cog):
    """Játékos csatlakozási parancsok."""

    def __init__(self, bot: commands.Bot, player_manager: PlayerManager) -> None:
        self.bot = bot
        self.manager = player_manager

    # ------------------------------------------------------------------
    # !join <karakternév>
    # ------------------------------------------------------------------
    @commands.command(name="join")
    async def join(self, ctx: commands.Context, *, character_name: str = "") -> None:
        """Csatlakozás a kampányhoz egy karakterrel.
        Használat: !join <karakternév>
        """
        if not character_name:
            await ctx.send("Add meg a karaktered nevét: `!join <karakternév>`")
            return

        result = self.manager.request_join(
            channel_id=str(ctx.channel.id),
            user_id=str(ctx.author.id),
            character_name=character_name.strip(),
        )
        if result["ok"]:
            await ctx.send(f"✅ {result['message']}")
        else:
            await ctx.send(f"❌ {result['message']}")

    # ------------------------------------------------------------------
    # !campaign approve @játékos
    # ------------------------------------------------------------------
    @commands.command(name="campaign_approve", aliases=["approve"])
    @commands.has_permissions(manage_guild=True)
    async def campaign_approve(self, ctx: commands.Context, member: discord.Member) -> None:
        """Jóváhagyja egy játékos csatlakozási kérelmét.
        Használat: !campaign approve @Játékos
        """
        result = self.manager.approve(
            channel_id=str(ctx.channel.id),
            user_id=str(member.id),
        )
        await ctx.send(f"{'✅' if result['ok'] else '❌'} {result['message']}")

    # ------------------------------------------------------------------
    # !campaign deny @játékos
    # ------------------------------------------------------------------
    @commands.command(name="campaign_deny", aliases=["deny"])
    @commands.has_permissions(manage_guild=True)
    async def campaign_deny(self, ctx: commands.Context, member: discord.Member) -> None:
        """Elutasítja egy játékos csatlakozási kérelmét.
        Használat: !campaign deny @Játékos
        """
        result = self.manager.deny(
            channel_id=str(ctx.channel.id),
            user_id=str(member.id),
        )
        await ctx.send(f"{'✅' if result['ok'] else '❌'} {result['message']}")

    # ------------------------------------------------------------------
    # !party – csapatlista megjelenítése
    # ------------------------------------------------------------------
    @commands.command(name="party")
    async def party(self, ctx: commands.Context) -> None:
        """Megjeleníti a jóváhagyott csapattagokat és a függő kérelmeket."""
        party = self.manager.list_party(str(ctx.channel.id))
        pending = self.manager.list_pending(str(ctx.channel.id))

        embed = discord.Embed(title="⚔️ Csapat", color=discord.Color.blue())

        if party:
            party_text = "\n".join(
                f"• <@{p['user_id']}> – **{p.get('character_name', 'Ismeretlen')}**"
                for p in party
            )
        else:
            party_text = "Még nincsenek csapattagok."

        if pending:
            pending_text = "\n".join(
                f"• <@{p['user_id']}> – **{p.get('character_name', 'Ismeretlen')}** (függőben)"
                for p in pending
            )
        else:
            pending_text = "Nincsenek függő kérelmek."

        embed.add_field(name="Csapattagok", value=party_text, inline=False)
        embed.add_field(name="Függő kérelmek", value=pending_text, inline=False)

        await ctx.send(embed=embed)