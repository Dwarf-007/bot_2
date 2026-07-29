"""Optional Discord Cog for Donjon web generation commands."""

from __future__ import annotations

import asyncio

from discord.ext import commands

from services.donjon.donjon_web_command_parser import DonjonWebCommandParser
from services.donjon.donjon_web_pipeline import DonjonWebPipeline


class DMDonjonWebCommands(commands.Cog):
    def __init__(self, bot, runtime):
        self.bot = bot
        self.runtime = runtime
        self.parser = DonjonWebCommandParser()
        self.pipeline = DonjonWebPipeline(runtime=runtime, llm_adapter=getattr(runtime, "llm_adapter", None))

    async def cog_check(self, ctx):
        return bool(ctx.guild and (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_guild))

    async def _send_chunked(self, ctx, text: str, chunk_size: int = 1800):
        value = str(text or "")
        for index in range(0, max(len(value), 1), chunk_size):
            await ctx.send(value[index:index + chunk_size] or "Nincs megjeleníthető adat.")

    @commands.command(name="dm_generate_donjon_web")
    async def dm_generate_donjon_web(self, ctx, *, args: str = ""):
        try:
            request, options = self.parser.parse(args)
            result = self.pipeline.generate_campaign_from_web(
                web_request=request,
                enrich=options.get("enrich", True),
                import_to_runtime=options.get("import_to_runtime", False),
                clear_rag=options.get("clear_rag", False),
                max_rooms=options.get("max_rooms"),
            )
            text = "**Donjon web generation finished**\n" + "```json\n" + str(result)[:1600] + "\n```"
        except Exception as exc:
            text = f"Donjon web generálás sikertelen: `{type(exc).__name__}: {exc}`\n" + self.help_text()
        await self._send_chunked(ctx, text)

    @commands.command(name="dm_generate_donjon_web_options")
    async def dm_generate_donjon_web_options(self, ctx):
        await self._send_chunked(ctx, self.parser.option_catalog_text())

    @commands.command(name="dm_generate_donjon_web_megadungeon")
    async def dm_generate_donjon_web_megadungeon(self, ctx, *, args: str = ""):
        await ctx.send(
            "Megadungeon generálás elindítva (ez hosszabb folyamat is lehet: "
            "szintenkénti donjon generálás + összefűzés)..."
        )
        try:
            import shlex
            await ctx.send(
                "Megadungeon generálás: "
            )
            from tools.generate_donjon_20_level_megadungeon import (
                build_parser,
                generate_and_download_levels,
                run_postprocess,
            )
            tokens = shlex.split(args or "")
            # --import -> --runtime-import (konzisztens a sima !dm_generate_donjon_web parancsal)
            normalized = ["--runtime-import" if t == "--import" else t for t in tokens]
            ns = build_parser().parse_args(normalized)
            manifest_path, _manifest = await asyncio.to_thread(generate_and_download_levels, ns)
            postprocess_result = None
            if ns.postprocess:
                postprocess_result = await asyncio.to_thread(run_postprocess, ns, manifest_path)
            text = (
                "**Donjon web MEGADUNGEON generálás kész**\n"
                f"Manifest: `{manifest_path}`\n"
                f"Szintek: `{ns.level_start}`–`{ns.level_end}`\n"
            )
            if postprocess_result is not None:
                text += f"Postprocess ok: `{postprocess_result.get('ok')}`\n"
            text += "Részletek a szerver konzolon / manifest fájlban."
        except SystemExit as exc:
            text = f"Hibás paraméterek a megadungeon generáláshoz: `{exc}`\n" + self.help_text()
        except Exception as exc:
            text = f"Megadungeon generálás sikertelen: `{type(exc).__name__}: {exc}`\n" + self.help_text()
        await self._send_chunked(ctx, text)

    @commands.command(name="dm_generate_donjon_web_megadungeon_help")
    async def dm_generate_donjon_web_megadungeon_help(self, ctx):
        await self._send_chunked(ctx, self.megadungeon_help_text())

    def megadungeon_help_text(self) -> str:
        return (
            "**!dm_generate_donjon_web_megadungeon használata**\n"
            "A megadott kezdő szinttől (--level-start, alapértelmezett 1) a megadott utolsó szintig "
            "(--level-end, alapértelmezett 20) donjon szintet generál, majd összefűzi őket egy megadungeon-né.\n\n"
            "Példa:\n"
            "`!dm_generate_donjon_web_megadungeon sakka --name \"Sakka\" --level-start 1 --level-end 20 "
            "--theme Undead --party-size 4 --room-size Medium --remove-deadends Some --runtime-import --clear-rag`\n\n"
            "Fontosabb kapcsolók:\n"
            "- `<campaign_id>` (kötelező pozicionális)\n"
            "- `--name` : kampány neve\n"
            "- `--level-start` / `--level-end` : szinttartomány (alapértelmezett 1 / 20)\n"
            "- `--theme` : motif (pl. Undead, Aberrant, Fire)\n"
            "- `--party-size` : 1-10\n"
            "- `--room-size` : Medium | Large\n"
            "- `--remove-deadends` : Some | None\n"
            "- `--seed` : opcionális fix seed\n"
            "- `--runtime-import` : a kész megadungeon importálása a runtime DB-be (a `--import` is működik)\n"
            "- `--clear-rag` : RAG törlése import előtt\n"
            "- `--no-postprocess` : csak generálás/letöltés, összefűzés nélkül\n"
            "Megjegyzés: a szerveren Playwright + Chromium szükséges."
        )

    def help_text(self) -> str:
        catalog = self.parser.option_catalog_text()
        return (
            "Használat:\n"
            "`!dm_generate_donjon_web sakka --name \"Sakka\" --theme Undead --size Large --import --clear-rag`\n"
            "Minden `--<opció> <érték>` paraméter támogatott (pl. --motif Undead, --room-layout Dense, --doors Standard, --grid Hex, --n-pc 4, --infest Many).\n"
            "A teljes opciólista: `!dm_generate_donjon_web_options`\n"
            "Megjegyzés: a szerveren Playwright + Chromium szükséges.\n\n"
            f"{catalog}"
        )
