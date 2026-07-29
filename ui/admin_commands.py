"""
ADMIN_COMMANDS.PY - A Discord adminisztrátori parancsokat kezelő modul.
Lehetővé teszi a kampányok, helyszínek és csatorna-állapotok dinamikus kezelését.
"""

import json
import discord
from discord.ext import commands
from typing import Optional

# Feltételezzük, hogy az adatbázis kapcsolatot egy külön modul kezeli tisztán
# Ha SQLite-ot használsz, a háttérben ez hívódik meg
import database as db 
from ui.character_view import CharacterActivationView


class AdminCommands(commands.Cog):
    """
    Discord.py Cog bővítmény, amely a Dungeon Master és a koordinátorok 
    számára biztosít kampánykezelő, adatbázis-módosító és UI indító parancsokat.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==============================================================================
    # 1. KAMPÁNY REGISZTRÁCIÓ ÉS LÉTREHOZÁS
    # ==============================================================================
    @commands.command(name="newcampaign")
    @commands.has_permissions(administrator=True)
    async def create_campaign(
        self, 
        ctx: commands.Context, 
        campaign_id: str, 
        module_name: str, 
        xp_mode: str = "MONSTER", 
        realism: str = "HYBRID"
    ):
        """
        Létrehoz egy új kampányt az adatbázisban.
        Példa: !newcampaign rappan_team_a "Rappan Athuk" MONSTER HYBRID
        """
        xp_mode_upper = xp_mode.upper()
        realism_upper = realism.upper()

        if xp_mode_upper not in ["MONSTER", "MILESTONE"] or realism_upper not in ["HARDCORE", "HYBRID", "CASUAL"]:
            await ctx.send("❌ **Hiba:** Érvénytelen XP mód (MONSTER/MILESTONE) vagy realizmus szint (HARDCORE/HYBRID/CASUAL)!")
            return

        with db.get_db_connection() as conn:
            conn.execute("""
                INSERT INTO Campaigns (campaign_id, module_name, xp_mode, inventory_realism)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(campaign_id) DO UPDATE SET 
                    module_name=excluded.module_name, 
                    xp_mode=excluded.xp_mode, 
                    inventory_realism=excluded.inventory_realism
            """, (campaign_id.lower(), module_name, xp_mode_upper, realism_upper))
            conn.commit()

        await ctx.send(
            f"✅ **Sikeres kampány regisztráció!**\n"
            f"🆔 ID: `{campaign_id.lower()}`\n"
            f"📘 Modul: `{module_name}`\n"
            f"🎯 XP: `{xp_mode_upper}`\n"
            f"🎒 Realizmus: `{realism_upper}`"
        )

    # ==============================================================================
    # 2. DISCORD CSATORNA HOZZÁRENDELÉSE A KAMPÁNYHOZ
    # ==============================================================================
    @commands.command(name="registerchannel")
    @commands.has_permissions(administrator=True)
    async def register_channel(self, ctx: commands.Context, campaign_id: str, start_room_id: str):
        """
        Az aktuális Discord csatornát hozzáláncolja egy kampányhoz és egy kezdőszobához.
        Példa: !registerchannel rappan_team_a level_1_room_4
        """
        channel_id = str(ctx.channel.id)
        campaign_id_lower = campaign_id.lower()

        with db.get_db_connection() as conn:
            # Ellenőrizzük, hogy létezik-e a megadott kampány az adatbázisban
            campaign_exists = conn.execute(
                "SELECT 1 FROM Campaigns WHERE campaign_id = ?", 
                (campaign_id_lower,)
            ).fetchone()
            
            if not campaign_exists:
                await ctx.send(f"❌ **Hiba:** Nem található `{campaign_id_lower}` azonosítójú kampány! Hozd létre előbb a `!newcampaign` paranccsal.")
                return

            # Regisztráljuk vagy frissítjük a csatorna állapotát
            conn.execute("""
                INSERT INTO Channel_States (channel_id, campaign_id, current_location_id)
                VALUES (?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET 
                    campaign_id=excluded.campaign_id, 
                    current_location_id=excluded.current_location_id
            """, (channel_id, campaign_id_lower, start_room_id))
            conn.commit()

        await ctx.send(
            f"🎮 **Ez a csatorna mostantól aktív játékos szoba!**\n"
            f"📌 Kampány: `{campaign_id_lower}`\n"
            f"📍 Jelenlegi helyszín: `{start_room_id}`"
        )

    # ==============================================================================
    # 3. FIX HELYSZÍNEK / SZOBÁK FELTÖLTÉSE (ADATBÁZIS ALAPÚ RAG-HEZ)
    # ==============================================================================
    @commands.command(name="addroom")
    @commands.has_permissions(administrator=True)
    async def add_room(self, ctx: commands.Context, campaign_id: str, room_id: str, title: str, *, facts: str):
        """
        Manuálisan hozzáad vagy frissít egy fix szobát az adatbázisban.
        Példa: !addroom rappan_team_a room_4 "A Trágyaszörny Szobája" Bűzös szoba, egy Dung Monster rejtőzik a szemétben.
        """
        # Alapértelmezett üres vagy standard struktúrák JSON stringként tárolva az adatbázisban
        default_exits = json.dumps({"észak": "level_1_room_5"})
        default_monsters = json.dumps(["Dung Monster"])

        with db.get_db_connection() as conn:
            conn.execute("""
                INSERT INTO Fixed_Locations (campaign_id, room_id, title, facts, exits, monsters, safe_zone)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(campaign_id, room_id) DO UPDATE SET 
                    title=excluded.title, 
                    facts=excluded.facts
            """, (campaign_id.lower(), room_id, title, facts, default_exits, default_monsters))
            conn.commit()

        await ctx.send(f"📥 **Szoba sikeresen rögzítve!**\n🏰 Szoba ID: `{room_id}`\n🏷️ Név: `{title}`")

    # ==============================================================================
    # 4. INTELLIGENS DINAMIKUS FINOMÍTÓ PARANCSOK
    # ==============================================================================
    @commands.command(name="setrealism")
    @commands.has_permissions(administrator=True)
    async def set_realism(self, ctx: commands.Context, mode: str):
        """Módosítja az inventory realizmus szintjét az aktuális csatorna kampányában."""
        mode_upper = mode.upper()
        if mode_upper not in ["HARDCORE", "HYBRID", "CASUAL"]:
            await ctx.send("❌ Érvénytelen mód! Válassz: `HARDCORE`, `HYBRID`, `CASUAL`")
            return

        channel_id = str(ctx.channel.id)
        with db.get_db_connection() as conn:
            state = conn.execute("SELECT campaign_id FROM Channel_States WHERE channel_id = ?", (channel_id,)).fetchone()
            if not state:
                await ctx.send("❌ Ez a csatorna nincs aktív játékhoz regisztrálva!")
                return
            
            conn.execute("UPDATE Campaigns SET inventory_realism = ? WHERE campaign_id = ?", (mode_upper, state["campaign_id"]))
            conn.commit()

        await ctx.send(f"🎒 **Inventory realizmus átállítva:** `{mode_upper}` módra a(z) `{state['campaign_id']}` kampányban.")

    @commands.command(name="setparty")
    @commands.has_permissions(administrator=True)
    async def set_party_stats(self, ctx: commands.Context, level: int, players: int):
        """Beállítja a csatornában lévő csapat szintjét és létszámát az AI skálázáshoz."""
        channel_id = str(ctx.channel.id)
        with db.get_db_connection() as conn:
            conn.execute("""
                UPDATE Channel_States 
                SET party_level = ?, player_count = ? 
                WHERE channel_id = ?
            """, (level, players, channel_id))
            conn.commit()

        await ctx.send(f"📊 **Csapat statisztikák frissítve!**\n👥 Létszám: `{players} fő`\n🛡️ Átlagos szint: `{level}. szint`")

    # ==============================================================================
    # 5. INTEGRÁLT INTERAKTÍV UI PARANCSOK (ÁTEMELVE A PÁRHUZAMOS MODULBÓL)
    # ==============================================================================
    @commands.command(name="setup_character")
    @commands.has_permissions(administrator=True)
    async def setup_character(self, ctx: commands.Context, player_mention: discord.Member, character_name: str, dndbeyond_id: str = "0"):
        """
        Létrehozza és kiküldi az interaktív gombot a karakter Avrae-aktiválásához.
        Példa: !setup_character @Játékos1 "Thorin" 12345678
        """
        avrae_commands = [
            f"!char import https://dndbeyond.com{dndbeyond_id}" if dndbeyond_id != "0" else f"!char create {character_name}",
            f"!char active {character_name}",
            "!gheet sheet"
        ]

        view = CharacterActivationView(commands_list=avrae_commands)

        embed = discord.Embed(
            title="🛡️ Karakter Inicializálása",
            description=f"Elkészült {player_mention.mention} új karaktere: **{character_name}**.",
            color=discord.Color.dark_red()
        )
        embed.add_field(
            name="Következő lépés:", 
            value="Kattints az alábbi gombra a karakter betöltéséhez az Avrae-be!",
            inline=False
        )

        await ctx.send(embed=embed, view=view)


# Cog regisztrációja a Discord.py rendszerébe
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))
