
"""
DATABASE.PY - Hardened SQLite persistence layer.

Responsibilities:
- Thread-safe connection handling
- Schema initialization and migration-safe creation
- Strongly typed CRUD operations
- Defensive defaults for absent rows
- JSON-safe serialization/deserialization

!!! No Discord or async code allowed here !!!
"""

import sqlite3
import json
from contextlib import contextmanager
from typing import Generator, Dict, Any, Optional

DB_FILE: str = "campaigns.db"


# =============================================================================
# CONNECTION MANAGEMENT
# =============================================================================

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for safe SQLite connections.

    - Enables foreign keys
    - Uses Row factory for dict-like access
    - Handles transaction rollback automatically
    """
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Enforce FK constraints
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =============================================================================
# SCHEMA INITIALIZATION
# =============================================================================

def initialize_database() -> None:
    """
    Creates all tables if they do not exist.
    Safe to call multiple times.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS Campaigns (
            campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_name TEXT,
            dm_style TEXT,
            scaling_enabled INTEGER,
            inventory_realism TEXT,
            xp_mode TEXT
        );

        CREATE TABLE IF NOT EXISTS Channel_States (
            channel_id TEXT PRIMARY KEY,
            campaign_id INTEGER,
            current_location_id TEXT,
            current_state TEXT,
            active_check TEXT,
            active_dc INTEGER,
            party_level INTEGER,
            players TEXT,
            visited_rooms TEXT,
            inventory_keys TEXT,
            style TEXT,
            difficulty TEXT,
            active_player TEXT,
            mode TEXT,
            context_window TEXT,
            player_count INTEGER,
            FOREIGN KEY (campaign_id) REFERENCES Campaigns(campaign_id)
        );

        CREATE TABLE IF NOT EXISTS Fixed_Locations (
            campaign_id INTEGER,
            room_id TEXT,
            title TEXT,
            facts TEXT,
            exits TEXT,
            monsters TEXT,
            safe_zone INTEGER,
            PRIMARY KEY (campaign_id, room_id)
        );

        CREATE TABLE IF NOT EXISTS Inventory (
            channel_id TEXT,
            player_id TEXT,
            gold REAL,
            items TEXT,
            ammo TEXT,
            PRIMARY KEY (channel_id, player_id)
        );

        CREATE TABLE IF NOT EXISTS Character_Levels (
            channel_id TEXT,
            player_id TEXT,
            current_xp INTEGER,
            current_level INTEGER,
            PRIMARY KEY (channel_id, player_id)
        );

        CREATE TABLE IF NOT EXISTS Global_Flags (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS Character_Builder_State (
            user_id TEXT PRIMARY KEY,
            state TEXT
        );
        
        CREATE TABLE IF NOT EXISTS Party_Members (
            channel_id TEXT,
            player_id TEXT,
            PRIMARY KEY (channel_id, player_id)
        );

        """)

        conn.commit()


# =============================================================================
# UTILITY HELPERS
# =============================================================================

def _safe_json_load(data: Optional[str]) -> Dict[str, Any]:
    if not data:
        return {}
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {}


def _safe_json_dump(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


# =============================================================================
# XP & LEVEL MANAGEMENT
# =============================================================================

def get_player_xp(channel_id: str, player_id: str) -> Dict[str, int]:
    """Fetch player XP and level with safe defaults."""
    with get_db_connection() as conn:
        row = conn.execute("""
            SELECT current_xp, current_level
            FROM Character_Levels
            WHERE channel_id=? AND player_id=?
        """, (channel_id, player_id)).fetchone()

        if row:
            return {
                "xp": row["current_xp"],
                "level": row["current_level"]
            }

    return {"xp": 0, "level": 1}


def add_player_xp(channel_id: str, player_id: str, xp: int) -> None:
    """Atomically adds XP to player."""
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO Character_Levels (channel_id, player_id, current_xp, current_level)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(channel_id, player_id)
            DO UPDATE SET current_xp = current_xp + excluded.current_xp
        """, (channel_id, player_id, xp))
        conn.commit()


def update_player_level(channel_id: str, player_id: str, new_level: int) -> None:
    """Updates player level."""
    with get_db_connection() as conn:
        conn.execute("""
            UPDATE Character_Levels
            SET current_level = ?
            WHERE channel_id = ? AND player_id = ?
        """, (new_level, channel_id, player_id))
        conn.commit()


# =============================================================================
# INVENTORY MANAGEMENT
# =============================================================================

def get_player_inventory(channel_id: str, player_id: str) -> Dict[str, Any]:
    """Fetch inventory with safe defaults."""
    with get_db_connection() as conn:
        row = conn.execute("""
            SELECT gold, items, ammo
            FROM Inventory
            WHERE channel_id=? AND player_id=?
        """, (channel_id, player_id)).fetchone()

        if row:
            return {
                "gold": row["gold"],
                "items": _safe_json_load(row["items"]),
                "ammo": _safe_json_load(row["ammo"])
            }

    return {
        "gold": 0.0,
        "items": {},
        "ammo": {}
    }


def save_player_inventory(channel_id: str, player_id: str, data: Dict[str, Any]) -> None:
    """Upserts player inventory atomically."""
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO Inventory (channel_id, player_id, gold, items, ammo)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(channel_id, player_id)
            DO UPDATE SET
                gold = excluded.gold,
                items = excluded.items,
                ammo = excluded.ammo
        """, (
            channel_id,
            player_id,
            float(data.get("gold", 0.0)),
            _safe_json_dump(data.get("items", {})),
            _safe_json_dump(data.get("ammo", {}))
        ))
        conn.commit()


# =============================================================================
# CHANNEL STATE
# =============================================================================


def get_or_create_channel_state(channel_id: str) -> Dict[str, Any]:

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM Channel_States WHERE channel_id=?",
            (channel_id,)
        ).fetchone()

        if not row:
            conn.execute(
                """INSERT INTO Channel_States (channel_id, current_state)
                   VALUES (?, 'EXPLORATION')""",
                (channel_id,)
            )
            conn.commit()
            return get_or_create_channel_state(channel_id)

    # ✅ SAFE JSON LOAD
    return {
        "current_state": row["current_state"],
        "current_location_id": row["current_location_id"],

        "players": _safe_json_load(row["players"]) or [],
        "trap_state": _safe_json_load(row["trap_state"]) or {},
        "visited_rooms": _safe_json_load(row["visited_rooms"]) or [],
        "inventory_keys": _safe_json_load(row["inventory_keys"]) or [],

        "style": row["style"] or "grimdark",
        "difficulty": row["difficulty"] or "standard",
        "mode": row["mode"] or "campaign",

        "context_window": _safe_json_load(row["context_window"]) or [],
        "active_player": row["active_player"]
    }



def update_channel_field(channel_id: str, field: str, value):

    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)

    with get_db_connection() as conn:
        conn.execute(
            f"UPDATE Channel_States SET {field}=? WHERE channel_id=?",
            (value, channel_id)
        )
        conn.commit()



def update_channel_state(channel_id: str, state: str) -> None:
    with get_db_connection() as conn:
        conn.execute("""
            UPDATE Channel_States
            SET current_state = ?
            WHERE channel_id = ?
        """, (state, channel_id))
        conn.commit()


def update_channel_location(channel_id: str, location_id: str) -> None:
    with get_db_connection() as conn:
        conn.execute("""
            UPDATE Channel_States
            SET current_location_id = ?
            WHERE channel_id = ?
        """, (location_id, channel_id))
        conn.commit()


def set_active_check(channel_id: str, check_name: str, dc: int) -> None:
    with get_db_connection() as conn:
        conn.execute("""
            UPDATE Channel_States
            SET active_check = ?, active_dc = ?
            WHERE channel_id = ?
        """, (check_name, dc, channel_id))
        conn.commit()


def clear_active_check(channel_id: str) -> None:
    with get_db_connection() as conn:
        conn.execute("""
            UPDATE Channel_States
            SET active_check='None', active_dc=0
            WHERE channel_id=?
        """, (channel_id,))
        conn.commit()


# =============================================================================
# LOCATION DATA
# =============================================================================

def get_room_facts(room_id: str) -> str:
    """Fetch RAG facts for a room."""
    with get_db_connection() as conn:
        row = conn.execute("""
            SELECT facts FROM Fixed_Locations WHERE room_id=?
        """, (room_id,)).fetchone()

        return row["facts"] if row else ""



