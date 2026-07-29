"""
BOT/BOT_CORE.PY

Discord bot wiring with Avrae feedback routing, legacy admin commands, and
optional generator/admin Cogs from Sprint 4-9.

C3.3 update:
- DiscordTurnRouter is no longer wired with avrae_dispatcher.
- Avrae feedback parsing may remain optional for incoming Avrae bot messages,
  but outgoing CombatRuntime/TurnOutput command suggestions are advisory only.
"""
from __future__ import annotations

import logging
import discord
from discord.ext import commands

from avrae.avrae_parser import AvraeParserService
from bot.admin_commands import DMAdminCommands
from bot.discord_router import DiscordTurnRouter
from services.campaign_manager import CampaignManager
from services.player_manager import PlayerManager
from bot.cogs.campaign_cog import CampaignCog
from bot.cogs.game_cog import GameCog
from bot.cogs.player_cog import PlayerCog


logger = logging.getLogger(__name__)


def create_bot(runtime, command_prefix: str = "!"):
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True
    bot = commands.Bot(command_prefix=command_prefix, intents=intents)

    # C3 boundary rule:
    # The Discord router must not receive or use an Avrae dispatcher for outgoing
    # command suggestions. Suggested commands are displayed for the DM only.
    router = DiscordTurnRouter(runtime.game_turn_service)

    @bot.event
    async def on_ready():
        print(f"✅ AI DM bot bejelentkezett: {bot.user}")

    @bot.event
    async def setup_hook():
        await bot.add_cog(DMAdminCommands(bot, runtime))
        print("🔧 AI DM admin/debug parancsok betöltve.")
        await _try_add_optional_cogs(bot, runtime)
        await bot.add_cog(CampaignCog(bot, runtime.campaign_manager))
        await bot.add_cog(PlayerCog(bot, runtime.player_manager))
        await bot.add_cog(GameCog(bot, runtime.campaign_manager, runtime.player_manager))

    @bot.event
    async def on_message(message):
        if message.author.bot:
            # Incoming Avrae feedback remains optional/advisory. It is not part
            # of outgoing command dispatch and does not make Avrae a required
            # CombatRuntime dependency.
            if runtime.combat_feedback_service and AvraeParserService.is_avrae_message(message):
                await runtime.combat_feedback_service.process_avrae_message(message)
            await bot.process_commands(message)
            return
        if not message.content:
            await bot.process_commands(message)
            return
        if message.content.startswith(command_prefix):
            await bot.process_commands(message)
            return
        await router.handle_player_message(message)
        await bot.process_commands(message)

    return bot


async def _try_add_optional_cogs(bot, runtime) -> None:
    """Register Sprint 4-9 Cogs when their files are installed.

    Missing generator packages should never prevent the base AI DM bot from
    starting.
    """
    optional_cogs = [
        ("bot.generate_commands", "DMGenerateCommands", "generator CLI/admin commands"),
        ("bot.donjon_web_commands", "DMDonjonWebCommands", "Donjon web commands"),
        ("bot.generator_admin_commands", "DMGeneratorAdminCommands", "generator health/artifacts commands"),
    ]
    for module_name, class_name, label in optional_cogs:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            await bot.add_cog(cls(bot, runtime))
            print(f"🔧 Opcionális Cog betöltve: {label}")
        except ModuleNotFoundError:
            logger.info("Optional Cog module not installed: %s", module_name)
        except Exception:
            logger.exception("Optional Cog registration failed: %s.%s", module_name, class_name)
