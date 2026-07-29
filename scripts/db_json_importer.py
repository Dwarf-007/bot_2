"""
DB_JSON_IMPORTER.PY - Kampánykönyvekből NotebookLM-mel kinyert adatok 
tömeges importálása strukturált JSON fájlból az SQLite adatbázisba.
"""

import os
import sys
import json
from typing import Dict, Any, List

# Biztosítjuk, hogy a script elérje a gyökérkönyvtárban lévő database modult
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database as db


def load_json_file(file_path: str) -> List[Dict[str, Any]]:
    """Beolvassa és validálja a forrás JSON fájlt."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"A megadott JSON import fájl nem található: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Ha a JSON egyetlen nagy objektum (szoba ID-k a kulcsok, mint a dungeon_map.json),
    # átalakítjuk listává az adatbázis-beszúráshoz.
    if isinstance(data, dict):
        formatted_list = []
        for room_id, room_data in data.items():
            item = {"room_id": room_id}
            item.update(room_data)
            formatted_list.append(item)
        return formatted_list
        
    return data


def import_campaign_data_from_json(json_filename: str, default_campaign_id: str = "rappan_team_a") -> None:
    """
    Végigiterál a JSON fájlban található helyszíneken és beírja őket az adatbázisba.
    Biztosítja, hogy az exits és monsters mezők érvényes JSON stringként tárolódjanak.
    """
    json_path = os.path.join(os.getcwd(), json_filename)
    
    try:
        rooms_list = load_json_file(json_path)
    except Exception as e:
        print(f"❌ Kritikus hiba a JSON beolvasása közben: {e}")
        return

    success_count = 0
    print(f"🔄 Tömeges importálás indítása: {json_filename} -> Fixed_Locations tábla...")

    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        for room in rooms_list:
            try:
                # Kötelező mezők ellenőrzése és kinyerése
                campaign_id = room.get("campaign_id", default_campaign_id).strip().lower()
                room_id = room["room_id"].strip()
                title = room["title"].strip()
                facts = room["facts"].strip()
                
                # Komplex JSON struktúrák (Kijáratok és Szörnyek) stringgé alakítása
                # Ha eleve stringként érkezik a NotebookLM-ből, megtartjuk, ha objektum/lista, dumpoljuk
                exits_data = room.get("exits", {})
                exits_json = exits_data if isinstance(exits_data, str) else json.dumps(exits_data, ensure_ascii=False)
                
                monsters_data = room.get("monsters", [])
                monsters_json = monsters_data if isinstance(monsters_data, str) else json.dumps(monsters_data, ensure_ascii=False)
                
                safe_zone = int(room.get("safe_zone", 0))

                # Biztonságos UPSERT SQL futtatás (Beszúrás vagy frissítés duplikáció nélkül)
                cursor.execute("""
                    INSERT INTO Fixed_Locations (campaign_id, room_id, title, facts, exits, monsters, safe_zone)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(campaign_id, room_id) DO UPDATE SET
                        title = excluded.title,
                        facts = excluded.facts,
                        exits = excluded.exits,
                        monsters = excluded.monsters,
                        safe_zone = excluded.safe_zone;
                """, (campaign_id, room_id, title, facts, exits_json, monsters_json, safe_zone))
                
                success_count += 1
                
            except KeyError as e:
                print(f"⚠️ Figyelmeztetés: Hiányzó kötelező mező {e} a következő szobánál: {room.get('room_id', 'Ismeretlen')}")
            except Exception as e:
                print(f"❌ Hiba a szoba feldolgozása közben ({room.get('room_id', 'Ismeretlen')}): {e}")

        conn.commit()

    print(f"✅ Sikeresen betöltve/frissítve: {success_count} helyszín.")


if __name__ == "__main__":
    # A projekt gyökerében elhelyezett import fájlt célozzuk meg
    import_file = "dungeon_import.json"
    import_campaign_data_from_json(import_file)

