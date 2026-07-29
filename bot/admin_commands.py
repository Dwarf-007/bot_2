
"""
BOT/ADMIN_COMMANDS.PY
Discord admin/debug commands with runtime health command.
"""

from __future__ import annotations

import discord
from discord.ext import commands


class DMAdminCommands(commands.Cog):
    def __init__(self, bot, runtime) -> None:
        self.bot = bot
        self.runtime = runtime
        self.admin_service = runtime.admin_debug_service

    async def cog_check(self, ctx: commands.Context) -> bool:
        if not ctx.guild:
            return False
        perms = ctx.author.guild_permissions
        return bool(perms.administrator or perms.manage_guild)

    @commands.command(name="dm_doctor")
    async def dm_doctor(self, ctx: commands.Context) -> None:
        await self._send_chunked(ctx, self.admin_service.health_text(str(ctx.channel.id)))

    @commands.command(name="dm_progress")
    async def dm_progress(self, ctx: commands.Context) -> None:
        await self._send_chunked(ctx, self.admin_service.progress_text(str(ctx.channel.id)))

    @commands.command(name="dm_scene_list")
    async def dm_scene_list(self, ctx: commands.Context) -> None:
        await self._send_chunked(ctx, self.admin_service.scene_list_text(str(ctx.channel.id)))

    @commands.command(name="dm_scene_set")
    async def dm_scene_set(self, ctx: commands.Context, scene_id: str) -> None:
        await ctx.send(self.admin_service.scene_set_text(str(ctx.channel.id), scene_id))

    @commands.command(name="dm_objective_add")
    async def dm_objective_add(self, ctx: commands.Context, *, text: str) -> None:
        await ctx.send(self.admin_service.objective_add_text(str(ctx.channel.id), text))

    @commands.command(name="dm_objective_done")
    async def dm_objective_done(self, ctx: commands.Context, objective_id: int) -> None:
        await ctx.send(self.admin_service.objective_done_text(objective_id))

    @commands.command(name="dm_state")
    async def dm_state(self, ctx: commands.Context) -> None:
        await self._send_chunked(ctx, self.admin_service.state_text(str(ctx.channel.id)))

    @commands.command(name="dm_set_room")
    async def dm_set_room(self, ctx: commands.Context, *, room: str) -> None:
        await ctx.send(self.admin_service.set_room(str(ctx.channel.id), room))

    @commands.command(name="dm_room")
    async def dm_room(self, ctx: commands.Context, *, room: str) -> None:
        await self._send_chunked(ctx, self.admin_service.room_text(room, channel_id=str(ctx.channel.id)))

    @commands.command(name="dm_room_find")
    async def dm_room_find(self, ctx: commands.Context, *, query: str) -> None:
        await self._send_chunked(ctx, self.admin_service.find_room_text(str(ctx.channel.id), query))

    @commands.command(name="dm_campaign_set")
    async def dm_campaign_set(self, ctx: commands.Context, campaign_id: str) -> None:
        await ctx.send(self.admin_service.campaign_set_text(str(ctx.channel.id), campaign_id))

    @commands.command(name="dm_campaign_status")
    async def dm_campaign_status(self, ctx: commands.Context) -> None:
        await self._send_chunked(ctx, self.admin_service.campaign_status_text(str(ctx.channel.id)))

    @commands.command(name="dm_campaign_list")
    async def dm_campaign_list(self, ctx: commands.Context) -> None:
        await self._send_chunked(ctx, self.admin_service.campaign_list_text())

    @commands.command(name="dm_mode")
    async def dm_mode(self, ctx: commands.Context, mode: str) -> None:
        await ctx.send(self.admin_service.set_mode(str(ctx.channel.id), mode))

    @commands.command(name="dm_style")
    async def dm_style(self, ctx: commands.Context, *, style: str) -> None:
        await ctx.send(self.admin_service.set_style(str(ctx.channel.id), style))

    @commands.command(name="dm_difficulty")
    async def dm_difficulty(self, ctx: commands.Context, difficulty: str) -> None:
        await ctx.send(self.admin_service.set_difficulty(str(ctx.channel.id), difficulty))

    @commands.command(name="dm_party")
    async def dm_party(self, ctx: commands.Context) -> None:
        await self._send_chunked(ctx, self.admin_service.party_text(str(ctx.channel.id)))

    @commands.command(name="dm_inventory")
    async def dm_inventory(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        target = member or ctx.author
        await self._send_chunked(ctx, self.admin_service.inventory_text(str(ctx.channel.id), str(target.id)))

    @commands.command(name="dm_memory_recent")
    async def dm_memory_recent(self, ctx: commands.Context, limit: int = 10) -> None:
        await self._send_chunked(ctx, self.admin_service.recent_memory_text(str(ctx.channel.id), max(1, min(int(limit or 10), 50))))

    @commands.command(name="dm_memory_clear")
    async def dm_memory_clear(self, ctx: commands.Context) -> None:
        await ctx.send(self.admin_service.clear_memory(str(ctx.channel.id)))

    @commands.command(name="dm_exit")
    async def dm_exit(self, ctx: commands.Context) -> None:
        await ctx.send(self.admin_service.exit_channel_text(str(ctx.channel.id)))

    @commands.command(name="dm_rag_search")
    async def dm_rag_search(self, ctx: commands.Context, *, query: str) -> None:
        state = self.runtime.channel_repo.get_state(str(ctx.channel.id))
        campaign_id = str(state.get("campaign_id") or "default")
        await self._send_chunked(ctx, self.admin_service.rag_search_text(query=query, campaign_id=campaign_id, limit=5))

    @commands.command(name="dm_help")
    async def dm_help(self, ctx: commands.Context) -> None:
        text = """
**AI DM admin/debug parancsok**

`!dm_doctor` — runtime health check
`!dm_progress` — kampány progress + nyitott objective-ek
`!dm_scene_list` — scene lista az aktív kampányban
`!dm_scene_set <scene_id>` — aktuális scene beállítása
`!dm_objective_add <text>` — objective hozzáadása
`!dm_objective_done <id>` — objective lezárása
`!dm_state` — aktuális channel state
`!dm_set_room <room_id vagy cím/alias>` — aktuális helyszín beállítása
`!dm_room <room_id vagy cím/alias>` — room megtekintése
`!dm_room_find <query>` — room alias keresés
`!dm_campaign_set <campaign_id>` — aktív kampány beállítása
`!dm_campaign_status` — aktív kampány státusz
`!dm_campaign_list` — regisztrált kampányok
`!dm_exit` — kilépés az aktív kampányból, vissza a kiválasztó állapotba
`!dm_rag_search <query>` — local RAG keresés
""".strip()
        await ctx.send(text)

    @staticmethod
    async def _send_chunked(ctx: commands.Context, text: str, chunk_size: int = 1800) -> None:
        value = str(text or "")
        if not value:
            await ctx.send("Nincs megjeleníthető adat.")
            return
        for start in range(0, len(value), chunk_size):
            await ctx.send(value[start : start + chunk_size])
