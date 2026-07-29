# bot/cogs/campaign_cog.py
from __future__ import annotations

import discord
from discord.ext import commands

from services.campaign_manager import CampaignManager


class CampaignCog(commands.Cog):
    """Kampánykezelő parancsok: lista, választás, indítás, lezárás."""

    def __init__(self, bot: commands.Bot, campaign_manager: CampaignManager) -> None:
        self.bot = bot
        self.manager = campaign_manager

    async def cog_check(self, ctx: commands.Context) -> bool:
        """Csak kiemelt jogosultságú felhasználók (Admin, Manage Guild) használhatják a kampányparancsokat."""
        if not ctx.guild:
            return False
        perms = ctx.author.guild_permissions
        return bool(perms.administrator or perms.manage_guild)

    # ------------------------------------------------------------------
    # !campaign list
    # ------------------------------------------------------------------
    @commands.command(name="campaign", aliases=["kampany"])
    async def campaign(self, ctx: commands.Context, action: str = "", *, args: str = "") -> None:
        """Kampánykezelő parancsok gyűjtője.
        Használat:
            !campaign list
            !campaign select <campaign_id> [--leveling xp|milestone]
            !campaign start
            !campaign end
        """
        action = action.lower().strip()
        if action == "list":
            await self._cmd_list(ctx)
        elif action == "select":
            await self._cmd_select(ctx, args)
        elif action == "start":
            await self._cmd_start(ctx)
        elif action == "end":
            await self._cmd_end(ctx)
        else:
            await ctx.send(
                "Érvénytelen parancs. Használat:\n"
                "`!campaign list` – elérhető kampányok listája\n"
                "`!campaign select <id> [--leveling xp|milestone]` – kampány kiválasztása\n"
                "`!campaign start` – játék indítása\n"
                "`!campaign end` – kampány lezárása"
            )

    async def _cmd_list(self, ctx: commands.Context) -> None:
        campaigns = self.manager.list_available_campaigns()
        if not campaigns:
            await ctx.send("Nincsenek elérhető kampányok. Helyezz el kampány bundle-öket a `campaigns/` mappában.")
            return

        embed = discord.Embed(
            title="📜 Elérhető kampányok",
            color=discord.Color.dark_gold(),
        )
        for camp in campaigns:
            name = camp.get("name", camp["campaign_id"])
            camp_type = camp.get("type", "ismeretlen")
            level = camp.get("recommended_starting_level")
            party = camp.get("recommended_party_size")
            desc = camp.get("description", "")[:200]

            value = f"**Típus:** {camp_type}\n"
            if level:
                value += f"**Ajánlott kezdőszint:** {level}\n"
            if party:
                value += f"**Ajánlott játékosszám:** {party} fő\n"
            if desc:
                value += f"*{desc}*\n"
            value += f"**Azonosító:** `{camp['campaign_id']}`"

            embed.add_field(name=name, value=value, inline=False)

        await ctx.send(embed=embed)

    async def _cmd_select(self, ctx: commands.Context, args: str) -> None:
        parts = args.split()
        if not parts:
            await ctx.send("Hiányzó kampány azonosító. Használat: `!campaign select <campaign_id> [--leveling xp|milestone]`")
            return

        campaign_id = parts[0]
        leveling_mode = "xp"

        # Opcionális szintlépési mód
        if len(parts) > 2 and parts[1] == "--leveling":
            mode = parts[2].lower()
            if mode in ("xp", "milestone"):
                leveling_mode = mode
            else:
                await ctx.send("Érvénytelen szintlépési mód. Lehet: `xp` vagy `milestone`. Alapértelmezett: xp")
                return

        result = self.manager.select_campaign(
            channel_id=str(ctx.channel.id),
            campaign_id=campaign_id,
            leveling_mode=leveling_mode,
        )
        if result["ok"]:
            await ctx.send(f"✅ {result['message']}")
        else:
            await ctx.send(f"❌ {result['message']}")

    async def _cmd_start(self, ctx: commands.Context) -> None:
        result = self.manager.start_campaign(str(ctx.channel.id))
        if result["ok"]:
            # Az indítás utáni kezdőszoba leírását embedben is megjeleníthetjük
            description = result.get("message", "")
            room = result.get("room", {})
            exits = result.get("exits", [])

            embed = discord.Embed(
                title="🎲 A kaland elkezdődött!",
                description=description,
                color=discord.Color.green(),
            )
            if room:
                embed.add_field(name="Helyszín", value=room.get("title", "Ismeretlen"), inline=False)
            if exits:
                exit_text = "\n".join(
                    f"• {e.get('direction', '?')}: {e.get('label', e.get('description', '?'))}"
                    for e in exits[:10]
                )
                embed.add_field(name="Látható kijáratok", value=exit_text or "Nincs", inline=False)

            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ {result['message']}")

    async def _cmd_end(self, ctx: commands.Context) -> None:
        result = self.manager.end_campaign(str(ctx.channel.id))
        if result["ok"]:
            await ctx.send(f"🛑 {result['message']}")
        else:
            await ctx.send(f"❌ {result['message']}")