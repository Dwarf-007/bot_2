"""
CHARACTER_LOGIC.PY - A karakterépítő folyamat maglogikáját (Core Domain) kezelő modul.
Felelős az LLM állapotgép menedzseléséért és az Avrae parancsok kinyeréséért.
"""

import re
from typing import List, Dict, Any, Tuple
from google.genai import types


def format_history_for_llm(chat_history: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Az adatbázisból betöltött nyers JSON listát átalakítja a Gemini API 
    által elvárt strukturált formátumra (Content types).
    Asszinkron Play-by-Post játékban ez biztosítja, hogy az AI pontosan emlékezzen a kontextusra.
    """
    formatted_contents = []
    for turn in chat_history:
        # A Gemini API elvárja a 'user' és 'model' szerepkörök (role) pontos megjelölését
        role = "user" if turn["sender"] == "player" else "model"
        formatted_contents.append({
            "role": role,
            "parts": [{"text": turn["text"]}]
        })
    return formatted_contents


def extract_avrae_commands(llm_response_text: str) -> List[str]:
    """
    Reguláris kifejezések (Regex) segítségével biztonságosan kivágja 
    az LLM válaszából az [AVRAE_COMMANDS] és [END_COMMANDS] közé zárt parancsokat.
    Ezt a listát kapja meg közvetlenül az ui/character_view.py a gomb vezérléséhez.
    """
    # Keresünk mindent, ami a két egyedi jelölő között van (beleértve az új sorokat is)
    match = re.search(r'\[AVRAE_COMMANDS\](.*?)\[END_COMMANDS\]', llm_response_text, re.DOTALL)
    
    if match:
        commands_block = match.group(1).strip()
        # Feldaraboljuk a blokkot sorokra, megtisztítjuk a felesleges szóközöktől, 
        # és kiszűrjük az esetleges üres sorokat.
        return [cmd.strip() for cmd in commands_block.split('\n') if cmd.strip()]
    
    return []


def clean_narrative_text(llm_response_text: str) -> str:
    """
    Eltávolítja a nyers kódblokkokat és az Avrae parancsjelölőket a szövegből, 
    hogy a játékos egy tiszta, szép, szerepjátékos narrációt lásson a Discordon.
    """
    # Eltávolítjuk a teljes parancsblokkot a jelölőkkel együtt
    clean_text = re.sub(r'\[AVRAE_COMMANDS\].*?\[END_COMMANDS\]', '', llm_response_text, flags=re.DOTALL)
    return clean_text.strip()


# ==============================================================================
# ÁLLAPOTGÉP (STATE MACHINE) ÉS FOLYAMATKEZELŐ
# ==============================================================================

async def process_character_builder_turn(
    user_id: str, 
    player_message: str, 
    db_module, 
    prompts_module, 
    gemini_client_service
) -> Tuple[str, List[str], bool]:
    """
    Lebonyolít egy teljes kört a karakterépítő folyamatban:
    1. Betölti az eddigi előzményeket az adatbázisból.
    2. Hozzáadja az új játékos üzenetet.
    3. Lekéri az AI válaszát a megfelelő Rendszer Prompttal.
    4. Elmenti a frissített előzményeket.
    5. Ellenőrzi, hogy elkészült-e a karakter (vannak-e Avrae parancsok).
    
    Visszatérési érték: (clean_text, avrae_commands, is_finished)
    """
    # 1. Előzmények lekérése a database.py (db_module) segítségével
    history, _ = db_module.get_character_builder_state(user_id)
    
    # Ha ez az első üzenet, inicializáljuk a folyamatot
    if not history:
        history = []
    
    # 2. Játékos üzenetének hozzáadása a helyi történethez
    history.append({"sender": "player", "text": player_message})
    
    # Formázás a Gemini API specifikációja szerint
    api_contents = format_history_for_llm(history)
    
    # Új google-genai SDK konfigurációs objektum beállítása
    config = types.GenerateContentConfig(
        system_instruction=prompts_module.CHARACTER_BUILDER_SYSTEM,
        temperature=0.7
    )
    
    # 3. Gemini API hívás végrehajtása a gemini_client burkolóján keresztül
    # A legújabb, rendkívül gyors és kedvező gemini-2.5-flash modellt használjuk
    response = gemini_client_service.client.models.generate_content(
        model="gemini-2.5-flash",
        contents=api_contents,
        config=config
    )
    
    llm_text = response.text if response.text else ""
    
    # AI válaszának hozzáadása a történethez
    history.append({"sender": "dm", "text": llm_text})
    
    # 4. Parancsok és a tiszta szöveg kinyerése
    avrae_commands = extract_avrae_commands(llm_text)
    is_finished = len(avrae_commands) > 0
    
    # 5. Állapot mentése az adatbázisba
    # Ha elkészültek a parancsok, az állapotot inaktívvá tesszük (is_active = 0)
    status = 0 if is_finished else 1
    db_module.save_character_builder_state(user_id, history, is_active=status)
    
    # Megtisztítjuk a szöveget a Discordra küldés előtt
    clean_text = clean_narrative_text(llm_text)
    
    return clean_text, avrae_commands, is_finished
