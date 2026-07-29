"""
BOT/GENERATOR_ADMIN_COMMANDS.PY

Sprint 9 compatibility layer for generator/runtime admin commands.

This Cog is intentionally optional and safe to register next to the existing
DMAdminCommands. It exposes the generator stack added in Sprint 4-8 without
changing the core play loop.
"""
from __future__ import annotations

from discord.ext import commands

try:
    from services.generators.generator_admin_status_service import GeneratorAdminStatusService
except Exception:  # pragma: no cover - optional sprint package may be absent
    GeneratorAdminStatusService = None

try:
    from services.generators.artifact_registry import ArtifactRegistry
except Exception:  # pragma: no cover
    ArtifactRegistry = None


class DMGeneratorAdminCommands(commands.Cog):
    def __init__(self, bot, runtime) -> None:
        self.bot = bot
        self.runtime = runtime
        self.generator_admin_service = (
            GeneratorAdminStatusService() if GeneratorAdminStatusService else None
        )

    async def cog_check(self, ctx: commands.Context) -> bool:
        if not ctx.guild:
            return False
        perms = ctx.author.guild_permissions
        return bool(perms.administrator or perms.manage_guild)

    @commands.command(name="dm_generator_health")
    async def dm_generator_health(self, ctx: commands.Context) -> None:
        if not self.generator_admin_service:
            await ctx.send("Generator admin service nincs telepítve. Alkalmazd a Sprint 8 csomagot.")
            return
        await self._send_chunked(ctx, self.generator_admin_service.health_text())

    @commands.command(name="dm_generator_providers")
    async def dm_generator_providers(self, ctx: commands.Context) -> None:
        if not self.generator_admin_service:
            await ctx.send("Generator provider registry nincs telepítve. Alkalmazd a Sprint 8 csomagot.")
            return
        await self._send_chunked(ctx, self.generator_admin_service.providers_text())

    @commands.command(name="dm_generator_artifacts")
    async def dm_generator_artifacts(self, ctx: commands.Context, campaign_id: str | None = None, limit: int = 10) -> None:
        if not ArtifactRegistry:
            await ctx.send("ArtifactRegistry nincs telepítve. Alkalmazd a Sprint 7 csomagot.")
            return
        rows = ArtifactRegistry().list(campaign_id=campaign_id, limit=max(1, min(int(limit or 10), 50)))
        if not rows:
            await ctx.send("Nincs generator artifact bejegyzés.")
            return
        lines = ["**Generator artifacts:**"]
        for row in rows:
            lines.append(
                f"- `{row.status}` `{row.provider}` campaign=`{row.campaign_id}` run=`{row.run_id}` output=`{row.output_dir}`"
            )
        await self._send_chunked(ctx, "\n".join(lines))

    @commands.command(name="dm_generator_help")
    async def dm_generator_help(self, ctx: commands.Context) -> None:
        await ctx.send(
            "**Generator admin parancsok**\n"
            "`!dm_generator_health` — generator stack health check\n"
            "`!dm_generator_providers` — elérhető generator providerek\n"
            "`!dm_generator_artifacts [campaign_id] [limit]` — generator futások artifact registry listája"
        )

    @staticmethod
    async def _send_chunked(ctx: commands.Context, text: str, chunk_size: int = 1800) -> None:
        value = str(text or "")
        if not value:
            await ctx.send("Nincs megjeleníthető adat.")
            return
        for start in range(0, len(value), chunk_size):
            await ctx.send(value[start:start + chunk_size])
