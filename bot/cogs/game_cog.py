# bot/cogs/game_cog.py
from __future__ import annotations

import discord
from discord.ext import commands
from typing import Optional
from services.campaign_manager import CampaignManager
from services.player_manager import PlayerManager


class GameCog(commands.Cog):
    """Játékmenet parancsok: mozgás, körülnézés, pihenés, térkép, keresés."""

    def __init__(
        self,
        bot: commands.Bot,
        campaign_manager: CampaignManager,
        player_manager: PlayerManager | None = None,
    ) -> None:
        self.bot = bot
        self.campaign_manager = campaign_manager
        self.player_manager = player_manager

    async def cog_check(self, ctx: commands.Context) -> bool:
        """Csak akkor engedi a parancsokat, ha van aktív dungeon session és a játékos a csapat tagja."""
        if not ctx.guild:
            return False
        session = self.campaign_manager.get_session(str(ctx.channel.id))
        if session is None:
            raise commands.CheckFailure("Nincs aktív játék ezen a csatornán. Használd a `!campaign select` és `!campaign start` parancsokat.")
        if self.player_manager and not self.player_manager.is_member(str(ctx.channel.id), str(ctx.author.id)):
            raise commands.CheckFailure("Nem vagy tagja a csapatnak. Kérd a DM-et, hogy vegyen fel a `!campaign approve` paranccsal.")
        return True

    # ------------------------------------------------------------------
    # !move <irány>
    # ------------------------------------------------------------------
    @commands.command(name="move", aliases=["megyek", "menj"])
    async def move(self, ctx: commands.Context, direction: str = "", choice: Optional[int] = None) -> None:
        """Mozgás egy adott irányba.
        Használat: !move north|south|east|west|up|down
        """
        if not direction:
            await ctx.send("Add meg az irányt: `!move <észak|dél|kelet|nyugat|fel|le>`")
            return

        if choice is None:
            parts = direction.split()
            if len(parts) == 2:
                direction = parts[0]
                try:
                    choice = int(parts[1])
                except ValueError:
                    pass

        direction = self._normalize_direction(direction)
        if direction is None:
            await ctx.send("Érvénytelen irány. Lehetséges: észak, dél, kelet, nyugat, fel, le.")
            return

        session = self.campaign_manager.get_session(str(ctx.channel.id))
        if not session:
            await ctx.send("Nincs aktív játék. Indítsd el a kampányt: `!campaign start`")
            return

        # Use GameTurnService to process the move command
        from services.game_turn_service import GameTurnService
        from app.bootstrap import build_runtime
        runtime = build_runtime()
        game_turn_service = runtime.game_turn_service

        # Process the move command through GameTurnService
        output = game_turn_service.process(
            channel_id=str(ctx.channel.id),
            player_id=str(ctx.author.id),
            text=f"move {direction}"
        )

        # Check if combat started and handle it
        if output.public_narrative and "combat started" in output.public_narrative.lower():
            # Extract combat narrative and commands from the output
            combat_narrative = output.public_narrative
            combat_commands = output.avrae_commands

            # Send combat narrative
            await ctx.send(combat_narrative)

            # Send combat commands
            for cmd in combat_commands:
                await ctx.send(cmd)

        # Send the turn output
        from bot.discord_router import DiscordTurnRouter
        discord_router = DiscordTurnRouter(game_turn_service)
        await discord_router.send_turn_output(ctx, output)

    # ------------------------------------------------------------------
    # !look
    # ------------------------------------------------------------------
    @commands.command(name="look", aliases=["nézz", "körülnéz"])
    async def look(self, ctx: commands.Context) -> None:
        """Körülnézés a jelenlegi helyszínen."""
        session = self.campaign_manager.get_session(str(ctx.channel.id))
        if not session:
            await ctx.send("Nincs aktív játék.")
            return

        result = session.look()
        if result["ok"]:
            await self._send_room_info(ctx, result)
        else:
            await ctx.send(f"❌ {result.get('message', 'Ismeretlen hiba.')}")

    # ------------------------------------------------------------------
    # !rest short|long
    # ------------------------------------------------------------------
    @commands.command(name="rest", aliases=["pihen", "pihenő"])
    async def rest(self, ctx: commands.Context, rest_type: str = "short") -> None:
        """Pihenés: short (rövid) vagy long (hosszú).
        Használat: !rest short|long
        """
        rest_type = rest_type.lower().strip()
        if rest_type not in ("short", "long", "rövid", "hosszú"):
            await ctx.send("Add meg a pihenő típusát: `!rest short` vagy `!rest long`")
            return

        if rest_type in ("rövid", "short"):
            rest_type = "short"
        else:
            rest_type = "long"

        session = self.campaign_manager.get_session(str(ctx.channel.id))
        if not session:
            await ctx.send("Nincs aktív játék.")
            return

        result = session.rest(rest_type)
        if result["ok"]:
            await ctx.send(f"✅ {result.get('message', 'Pihenő vége.')}")
            if result.get("encounter"):
                await ctx.send("⚔️ **Véletlen találkozás a pihenő alatt!**")
        else:
            await ctx.send(f"❌ {result.get('message', 'Ismeretlen hiba.')}")

    # ------------------------------------------------------------------
    # !map
    # ------------------------------------------------------------------
    @commands.command(name="map", aliases=["térkép"])
    async def map(self, ctx: commands.Context) -> None:
        """A felfedezett terület térképének megjelenítése."""
        session = self.campaign_manager.get_session(str(ctx.channel.id))
        if not session:
            await ctx.send("Nincs aktív játék.")
            return

        map_file = session.render_map()
        if map_file:
            await ctx.send(file=discord.File(map_file))
        else:
            await ctx.send("❌ A térkép renderelése nem sikerült.")

    # ------------------------------------------------------------------
    # !search
    # ------------------------------------------------------------------
    @commands.command(name="search", aliases=["keres", "kutatok"])
    async def search(self, ctx: commands.Context, search_type: str = "secret") -> None:
        """Keresés: secret (titkosajtó), trap (csapda), treasure (kincs)."""
        search_type = search_type.lower().strip()
        if search_type not in ("secret", "trap", "treasure"):
            await ctx.send("Add meg a keresés típusát: `!search secret|trap|treasure`")
            return
        session = self.campaign_manager.get_session(str(ctx.channel.id))
        if not session:
            await ctx.send("Nincs aktív játék.")
            return
        result = session.search(search_type=search_type)
        await ctx.send(f"{'✅' if result.get('ok') else '❌'} {result.get('message', 'Ismeretlen hiba.')}")

    # ------------------------------------------------------------------
    # !open
    # ------------------------------------------------------------------
    @commands.command(name="open", aliases=["nyit", "kinyit"])
    async def open_door(self, ctx: commands.Context, direction: str = "") -> None:
        """Ajtó kinyitása egy adott irányba.
        Használat: !open east
        """
        if not direction:
            await ctx.send("Add meg az irányt: `!open <észak|dél|kelet|nyugat>`")
            return

        direction = self._normalize_direction(direction)
        if direction is None:
            await ctx.send("Érvénytelen irány. Lehetséges: észak, dél, kelet, nyugat, fel, le.")
            return

        session = self.campaign_manager.get_session(str(ctx.channel.id))
        if not session:
            await ctx.send("Nincs aktív játék.")
            return

        result = session.open_door(direction)
        if result["ok"]:
            await ctx.send(f"✅ {result['message']}")
        else:
            await ctx.send(f"❌ {result['message']}")

    # ------------------------------------------------------------------
    # Segédfüggvények
    # ------------------------------------------------------------------
    async def _send_room_info(self, ctx: commands.Context, result: dict) -> None:
        node = result.get("node", {})
        description = result.get("description", "")
        exits = result.get("exits", [])
        node_type = result.get("node_type", "")
        monsters = result.get("monsters", [])

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

        await ctx.send(embed=embed)

    @staticmethod
    def _normalize_direction(direction: str) -> str | None:
        """Magyar és angol irányok egységesítése."""
        mapping = {
            "észak": "north", "north": "north", "n": "north",
            "dél": "south", "south": "south", "s": "south",
            "kelet": "east", "east": "east", "e": "east",
            "nyugat": "west", "west": "west", "w": "west",
            "fel": "up", "up": "up",
            "le": "down", "down": "down",
        }
        return mapping.get(direction.lower())