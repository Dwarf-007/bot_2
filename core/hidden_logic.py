"""
HIDDEN_LOGIC.PY - A rejtett mechanikákat, automata háttérdobásokat 
és a privát csatornák szinkronizációját kezelő rendszermag.
"""

import re
import random
import discord
from discord.ext import commands
from typing import Tuple, Optional


class HiddenLogicService:
    """
    Felelős a passzív statisztikák alapján lefutó rejtett kockadobásokért,
    az AI zárt üzeneteinek DM-be történő továbbításáért és az Avrae HP-szinkronért.
    """

    @staticmethod
    def execute_secret_trap_check(room_data: dict, player_passive_perception: int = 10) -> str:
        """
        Lefuttat egy teljesen rejtett háttérdobást a csapda észlelésére vagy aktiválódására.
        Visszatérési érték: Egy injektálható rejtett prompt szöveg a Gemini számára.
        """
        facts = room_data.get("facts", "")
        
        # Ha a szoba leírásában nincs utalás csapdára, nem generálunk rejtett adatot
        if "csapda" not in facts.lower() and "trap" not in facts.lower():
            return ""

        # Alapértelmezett csapdaértékek (ha a JSON nem definiálja külön, regex-szel keressük a DC-t)
        dc_match = re.search(r'dc\s*(\d+)', facts.lower())
        dc_value = int(dc_match.group(1)) if dc_match else 14
        
        # 1. LÉPÉS: Passzív észlelés ellenőrzése
        detected = player_passive_perception >= dc_value
        detection_text = (
            f"- A játékos passzív észlelése ({player_passive_perception}) "
            f"{'ELÉRTE' if detected else 'NEM ÉRTE EL'} a célszámot (DC {dc_value}). "
            f"{'Kiszúrta a csapdát!' if detected else 'Gyanútlanul besétált.'}"
        )

        # 2. LÉPÉS: Ha nem vette észre, lefut a háttérdobás (Mentődobás + Sebzés)
        roll_context = ""
        if not detected:
            d20_roll = random.randint(1, 20)
            modifier = 3  # Átlagos mentődobás módosító
            total_save = d20_roll + modifier
            save_success = total_save >= dc_value
            
            damage_roll = random.randint(1, 10)  # 1d10 csapda sebzés
            
            roll_context = (
                f"\n- AUTOMATA HÁTTÉRMENTŐDOBÁS: d20({d20_roll}) + {modifier} = {total_save}. "
                f"Eredmény: {'SIKER (Félreugrott)' if save_success else 'ELBUKTA (Találat!)'}.\n"
                f"- CSAPDA SEBZÉSE: {0 if save_success else damage_roll} életerőpont."
            )
            
            # Ha elbukta, egy rejtett jelölőt is fűzünk hozzá az Avrae szinkronhoz
            if not save_success:
                roll_context += f"\n[AVRAE_SYNC_DAMAGE:{damage_roll}]"

        return f"\n[REJTETT ADATOK ÉS AUTOMATA HÁTTÉRDOBÁS]:\n{detection_text}{roll_context}\n"

    @staticmethod
    async def handle_hidden_information(
        message: discord.Message, 
        llm_response_text: str, 
        bot: commands.Bot
    ) -> str:
        """
        Megvizsgálja, hogy a Gemini válasza tartalmaz-e titkos információt egy adott játékosnak.
        Kiküldi privát üzenetben, majd megtisztítja a nyilvános chat szöveget.
        """
        # Keresgélés a [SECRET_TO: 123456789] mintára
        match = re.search(r'\[SECRET_TO:\s*(\d+)\](.*)', llm_response_text, re.DOTALL)
        
        if match:
            target_user_id = int(match.group(1))
            secret_message = match.group(2).strip()
            
            try:
                # 1. Elküldjük a titkos információt PRIVÁT ÜZENETBEN (DM) a játékosnak
                user = await bot.fetch_user(target_user_id)
                if user:
                    await user.send(f"👁️ **Titkos információ (Csak neked a(z) #{message.channel.name} szobából):**\n{secret_message}")
            except discord.Forbidden:
                print(f"⚠️ Nem sikerült PM-et küldeni a következő ID-ra: {target_user_id} (Le van tiltva a DM).")
                
            # 2. Megtisztítjuk a nyilvános chat szöveget, levágva a titkos részt
            public_text = re.sub(r'\[SECRET_TO:.*', '', llm_response_text, flags=re.DOTALL).strip()
            return public_text
            
        return llm_response_text

    @staticmethod
    async def sync_damage_to_avrae(message: discord.Message, llm_response_text: str) -> None:
        """
        Kiszűri a [AVRAE_SYNC_DAMAGE:X] jelölőt a háttéradatokból, és ha a karakter megsérült,
        a háttérben automatikusan kiadja a sebző parancsot az Avrae botnak.
        """
        match = re.search(r'\[AVRAE_SYNC_DAMAGE:\s*(\d+)\]', llm_response_text)
        if match:
            damage_amount = int(match.group(1))
            player_name = message.author.name
            # Kiküldjük a parancsot a csatornára gépies csendben az Avrae-nek
            await message.channel.send(f"!damage {player_name} {damage_amount}")
