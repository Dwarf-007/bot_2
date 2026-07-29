"""
BOT/GENERATE_COMMANDS.PY

Optional Discord Cog for Sprint 4 generation commands.

This file is separate from the existing bot/admin_commands.py skeleton, so it can
be registered later without breaking the current baseline.
"""

from __future__ import annotations

from discord.ext import commands

from services.generators.generation_admin_service import GenerationAdminService


class DMGenerateCommands(commands.Cog):
    def __init__(self, bot, runtime):
        self.bot = bot
        self.runtime = runtime
        self.generation_service = GenerationAdminService(
            runtime=runtime,
            llm_adapter=getattr(runtime, "llm_adapter", None),
        )

    async def cog_check(self, ctx):
        return bool(ctx.guild and (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_guild))

    async def _send_chunked(self, ctx, text: str, chunk_size: int = 1800):
        value = str(text or "")
        if not value:
            await ctx.send("Nincs megjeleníthető adat.")
            return
        for index in range(0, len(value), chunk_size):
            await ctx.send(value[index:index + chunk_size])

    @commands.command(name="dm_generate")
    async def dm_generate(self, ctx, *, args: str = ""):
        try:
            text = self.generation_service.generate_text(args)
        except Exception as exc:
            text = f"Generálás sikertelen: `{type(exc).__name__}: {exc}`\n\n{GenerationAdminService.help_text()}"
        await self._send_chunked(ctx, text)

    @commands.command(name="dm_generate_help")
    async def dm_generate_help(self, ctx):
        await self._send_chunked(ctx, GenerationAdminService.help_text())
