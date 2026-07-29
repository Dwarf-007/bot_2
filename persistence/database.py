"""
PERSISTENCE/DATABASE.PY
Hardened SQLite persistence layer for the AI DM engine.

Responsibilities:
- Connection management
- Schema initialization
- JSON serialization helpers
- No Discord code
- No LLM code

Repositories should use this module as their low-level DB dependency.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
from typing import Any, Dict, Generator, Optional

DB_FILE = "campaigns.db"


@contextmanager
def get_db_connection(db_file: str = DB_FILE) -> Generator[sqlite3.Connection, None, None]:
    """
    Opens a SQLite connection with safe defaults.

    Notes:
        - row_factory enables dict-like column access.
        - WAL improves concurrent reading for Discord bot workloads.
        - foreign_keys is enabled for future schema constraints.
    """

    db_path = Path(db_file)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
    finally:
        conn.close()


def initialize_database() -> None:
    """
    Creates all MVP tables if they do not exist.
    Safe to call multiple times during bot startup.
    """

    with get_db_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS Channel_States (
                channel_id TEXT PRIMARY KEY,
                current_state TEXT NOT NULL DEFAULT 'EXPLORATION',
                current_location_id TEXT,
                players_json TEXT NOT NULL DEFAULT '[]',
                active_player TEXT,
                visited_rooms_json TEXT NOT NULL DEFAULT '[]',
                inventory_keys_json TEXT NOT NULL DEFAULT '[]',
                trap_state_json TEXT NOT NULL DEFAULT '{}',
                mode TEXT NOT NULL DEFAULT 'campaign',
                style TEXT NOT NULL DEFAULT 'grimdark',
                difficulty TEXT NOT NULL DEFAULT 'standard',
                context_window_json TEXT NOT NULL DEFAULT '[]',
                active_check TEXT NOT NULL DEFAULT 'None',
                active_dc INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS Party_Members (
                channel_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_id, player_id)
            );

            CREATE TABLE IF NOT EXISTS Character_Levels (
                channel_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                current_xp INTEGER NOT NULL DEFAULT 0,
                current_level INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_id, player_id)
            );

            CREATE TABLE IF NOT EXISTS Inventory (
                channel_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                gold REAL NOT NULL DEFAULT 0,
                items_json TEXT NOT NULL DEFAULT '{}',
                ammo_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_id, player_id)
            );

            CREATE TABLE IF NOT EXISTS Fixed_Locations (
                room_id TEXT PRIMARY KEY,
                campaign_id TEXT NOT NULL DEFAULT 'default',
                title TEXT NOT NULL DEFAULT '',
                facts TEXT NOT NULL DEFAULT '',
                exits_json TEXT NOT NULL DEFAULT '{}',
                monsters_json TEXT NOT NULL DEFAULT '[]',
                raw_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS Memory_Events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                data_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()


def safe_json_load(data: Optional[str], default: Any) -> Any:
    if data is None or data == "":
        return default
    try:
        return json.loads(data)
    except (TypeError, json.JSONDecodeError):
        return default


def safe_json_dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def row_to_dict(row: sqlite3.Row | None) -> Dict[str, Any]:
    if row is None:
        return {}
    return {key: row[key] for key in row.keys()}
