"""
BOT/DISCORD_ROUTER.PY
Discord adapter helpers for sending TurnOutput.

This module is intentionally thin: all game logic remains in services/.

C3.2 update:
- The router no longer dispatches Avrae commands automatically.
- DM-facing instructions and suggested commands are rendered as advisory output.
- Legacy TurnOutput.avrae_commands are still displayed as copy/paste suggestions.
"""

from __future__ import annotations

from core.turn_output import TurnOutput


class DiscordTurnRouter:
    def __init__(self, game_turn_service, avrae_dispatcher=None) -> None:
        self.game_turn_service = game_turn_service
        # Kept for constructor compatibility only.
        # C3 boundary rule: do not auto-dispatch Avrae commands from this router.
        self.avrae_dispatcher = avrae_dispatcher

    async def handle_player_message(self, message) -> None:
        output = self.game_turn_service.process(
            channel_id=str(message.channel.id),
            player_id=str(message.author.id),
            text=message.content or "",
        )
        await self.send_turn_output(message, output)

    async def send_turn_output(self, message, output: TurnOutput) -> None:
        if output.public_narrative:
            await message.channel.send(output.public_narrative)

        # Check if the output contains room info and send as embed
        if hasattr(output, 'room_info') and output.room_info:
            await self._send_room_info(message, output.room_info)

        guidance_block = self._format_dm_guidance(output)
        if guidance_block:
            await message.channel.send(guidance_block)

        for secret in output.secret_messages:
            await self._send_secret_message(message, secret.player_id, secret.text)

    @staticmethod
    def _format_dm_guidance(output: TurnOutput) -> str:
        """
        Format DM-facing guidance as Discord text.

        C3 boundary rule:
        Commands are displayed for the DM to copy/paste manually. They are not
        dispatched to Avrae by the AI-DM runtime.
        """
        parts: list[str] = []

        if output.dm_instructions:
            instructions = "\n".join(f"- {item}" for item in output.dm_instructions if str(item).strip())
            if instructions:
                parts.append(f"**DM instrukció**{instructions}")

        commands = output.all_suggested_commands() if hasattr(output, "all_suggested_commands") else []
        if not commands:
            legacy_commands = getattr(output, "avrae_commands", []) or []
            commands = [str(command).strip() for command in legacy_commands if str(command).strip()]

        if commands:
            command_block = "\n".join(commands)
            parts.append(
                "**Javasolt DM / Avrae parancsok**"
                "```text"
                f"{command_block}"
                "```"
                "_Az AI-DM nem hajtja végre automatikusan ezeket a parancsokat._"
            )

        return "\n".join(parts)

    @staticmethod
    async def _send_room_info(message, room_info: dict) -> None:
        import discord
        node = room_info.get("node", {})
        description = room_info.get("description", "")
        exits = room_info.get("exits", [])
        node_type = room_info.get("node_type", "")
        monsters = room_info.get("monsters", [])

        if node_type == "room":
            title = node.get("title", "Ismeretlen szoba")
        elif node_type == "corridor":
            title = "Folyosó"
        elif node_type == "stairs_landing":
            title = "Lépcső"
        elif node_type == "outside":
            title = "Külvilág"
        else:
            title = node.get("title", "Ismeretlen")

        embed = discord.Embed(
            title=f"📍 {title}",
            description=description[:2000] if description else "...",
            color=discord.Color.dark_teal(),
        )

        if exits:
            exit_lines = []
            for i, e in enumerate(exits[:15], start=1):
                label = e.get("label") or e.get("description", "?")
                direction = e.get("direction", "?")
                exit_lines.append(f"**{i}.** {direction}**: {label}")
            embed.add_field(name="🚪 Látható kijáratok", value="\n".join(exit_lines), inline=False)
        else:
            embed.add_field(name="🚪 Látható kijáratok", value="Nincsenek látható kijáratok.", inline=False)

        if monsters:
            monster_names = []
            for m in monsters:
                if isinstance(m, str):
                    # String formátum: "2 x Stirge (cr 1/8, mm 284); ..."
                    monster_names.append(m.split("(cr")[0].strip())
                elif isinstance(m, dict):
                    monster_names.append(m.get("name", "Ismeretlen szörny"))
            if monster_names:
                embed.add_field(name="⚠️ Veszély", value=", ".join(monster_names), inline=False)

        await message.channel.send(embed=embed)

    @staticmethod
    async def _send_secret_message(message, player_id: str, text: str) -> None:
        try:
            guild = getattr(message, "guild", None)
            member = guild.get_member(int(player_id)) if guild else None
            user = member or await message.client.fetch_user(int(player_id))
            if user:
                await user.send(f"👁️ **Titkos információ:**{text}")
        except Exception:
            # Do not break the public game flow if a DM cannot be delivered.
            await message.channel.send(f"⚠️ Nem sikerült privát üzenetet küldeni ennek a játékosnak: <@{player_id}>")
