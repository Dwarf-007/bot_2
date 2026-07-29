"""
MAIN.PY
Stable entrypoint for the refactored AI DM Discord bot.
"""

from __future__ import annotations

from dotenv import load_dotenv

from app.bootstrap import build_runtime, register_discord_subscribers
from bot.bot_core import create_bot
from config import load_config
from utils.logging_config import configure_logging


def main() -> None:
    load_dotenv()
    config = load_config(require_discord_token=True)
    configure_logging(level=config.log_level, log_file=config.log_file)

    runtime = build_runtime(config=config)
    bot = create_bot(runtime, command_prefix=config.discord_command_prefix)
    register_discord_subscribers(runtime, bot)
    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
