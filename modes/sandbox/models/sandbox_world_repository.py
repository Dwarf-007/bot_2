"""
MODES/SANDBOX/REPOSITORIES/SANDBOX_WORLD_REPOSITORY.PY

Sprint 14.4 - Persistence layer for Sandbox Mode.

Storage conventions (mirrors persistence/database.py and existing
repositories such as ChannelRepository, CampaignProgressRepository,
LocationRepository):

- Every repository in this project takes a `db_module` dependency exposing
  `get_db_connection()`, `safe_json_dump(data)`, and
  `safe_json_load(data, default)`. This repository follows the same
  contract (see repositories/base.py BaseRepository).
- Complex/structured Python values are stored as opaque JSON text columns
  using the existing '<field>_json' naming convention already used by
  Channel_State.state_json, Fixed_Locations.raw_json,
  Campaign_Scenes.metadata_json, etc.:
    * Dict[str, Any] fields (global_flags, relationships, dispositions,
      metadata) -> stored as a single JSON object text column.
    * List[str] fields (goals, memory_logs, connected_locations,
      revealed_facts) -> stored as a JSON array text column.
    * Set[str] fields (discovered_location_ids, known_npc_ids,
      known_faction_ids) -> stored as a JSON array of the *sorted* set
      contents (sets are not JSON-serializable directly), and rehydrated
      into a Python set() on load.
    * bool fields (discovered) -> stored as INTEGER 0/1, same convention as
      Fixed_Locations.safe_zone / Combat_States.active.
- Every table uses a composite PRIMARY KEY of (campaign_id, <entity>_id),
  except Sandbox_World_State (PRIMARY KEY campaign_id) and
  Sandbox_Knowledge_Fog (PRIMARY KEY (channel_id, player_id)), matching the
  existing Inventory / Character_Levels / Party_Members composite-key
  pattern.
- Each table has an `updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`
  column, matching every other table added since Sprint 10
  (Campaign_Scenes, Channel_Progress, Combat_States, Room_Aliases, ...).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from repositories.base import BaseRepository
from modes.sandbox.models.sandbox_world_state import (
    SandboxFaction,
    SandboxLocation,
    SandboxNPC,
    SandboxWorldState,
)
from modes.sandbox.models.sandbox_knowledge_fog import SandboxKnowledgeFog


class SandboxWorldRepository(BaseRepository):
    """SQLite-backed persistence for Sandbox Mode world state."""

    # =========================================================================
    # SCHEMA
    # =========================================================================

    def ensure_schema(self) -> None:
        with self.db.get_db_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS Sandbox_World_State (
                    campaign_id TEXT PRIMARY KEY,
                    current_region TEXT,
                    game_time TEXT NOT NULL DEFAULT '',
                    global_flags_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS Sandbox_Locations (
                    campaign_id TEXT NOT NULL,
                    location_id TEXT NOT NULL,
                    parent_id TEXT,
                    title TEXT NOT NULL DEFAULT '',
                    facts TEXT NOT NULL DEFAULT '',
                    discovered INTEGER NOT NULL DEFAULT 0,
                    connected_locations_json TEXT NOT NULL DEFAULT '[]',
                    linked_dungeon_id TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (campaign_id, location_id)
                );

                CREATE INDEX IF NOT EXISTS idx_sandbox_locations_parent
                ON Sandbox_Locations(campaign_id, parent_id);

                CREATE TABLE IF NOT EXISTS Sandbox_NPCs (
                    campaign_id TEXT NOT NULL,
                    npc_id TEXT NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    current_location_id TEXT,
                    relationships_json TEXT NOT NULL DEFAULT '{}',
                    memory_logs_json TEXT NOT NULL DEFAULT '[]',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (campaign_id, npc_id)
                );

                CREATE INDEX IF NOT EXISTS idx_sandbox_npcs_location
                ON Sandbox_NPCs(campaign_id, current_location_id);

                CREATE TABLE IF NOT EXISTS Sandbox_Factions (
                    campaign_id TEXT NOT NULL,
                    faction_id TEXT NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    goals_json TEXT NOT NULL DEFAULT '[]',
                    dispositions_json TEXT NOT NULL DEFAULT '{}',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (campaign_id, faction_id)
                );

                CREATE TABLE IF NOT EXISTS Sandbox_Knowledge_Fog (
                    channel_id TEXT NOT NULL,
                    player_id TEXT NOT NULL DEFAULT '',
                    discovered_location_ids_json TEXT NOT NULL DEFAULT '[]',
                    known_npc_ids_json TEXT NOT NULL DEFAULT '[]',
                    known_faction_ids_json TEXT NOT NULL DEFAULT '[]',
                    revealed_facts_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (channel_id, player_id)
                );
                """
            )
            conn.commit()

    # =========================================================================
    # WORLD STATE
    # =========================================================================

    def save_world_state(self, state: SandboxWorldState) -> None:
        """
        Persists the world-level row (current_region/game_time/global_flags)
        and cascades into saving every embedded location/NPC/faction.

        Note: this performs a full save of all embedded entities every call.
        Callers that only mutated a single location/NPC/faction may prefer to
        call save_location()/save_npc()/save_faction() directly for a
        cheaper write.
        """
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Sandbox_World_State (
                    campaign_id, current_region, game_time, global_flags_json
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(campaign_id)
                DO UPDATE SET
                    current_region = excluded.current_region,
                    game_time = excluded.game_time,
                    global_flags_json = excluded.global_flags_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    str(state.campaign_id),
                    self._optional_str(state.current_region),
                    str(state.game_time or ""),
                    self.db.safe_json_dump(dict(state.global_flags or {})),
                ),
            )
            conn.commit()

        for location in state.locations.values():
            self.save_location(location)
        for npc in state.npcs.values():
            self.save_npc(npc)
        for faction in state.factions.values():
            self.save_faction(faction)

    def load_world_state(self, campaign_id: str) -> Optional[SandboxWorldState]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT campaign_id, current_region, game_time, global_flags_json
                FROM Sandbox_World_State
                WHERE campaign_id = ?
                """,
                (str(campaign_id),),
            ).fetchone()

        if not row:
            return None

        locations = {
            location.location_id: location
            for location in self.list_locations(campaign_id)
        }
        npcs = {
            npc.npc_id: npc
            for npc in self._list_all_npcs(campaign_id)
        }
        factions = {
            faction.faction_id: faction
            for faction in self.list_factions(campaign_id)
        }

        return SandboxWorldState(
            campaign_id=str(row["campaign_id"]),
            current_region=row["current_region"],
            game_time=str(row["game_time"] or ""),
            global_flags=self.db.safe_json_load(row["global_flags_json"], {}),
            locations=locations,
            npcs=npcs,
            factions=factions,
        )

    def get_or_create_world_state(self, campaign_id: str) -> SandboxWorldState:
        existing = self.load_world_state(campaign_id)
        if existing is not None:
            return existing

        state = SandboxWorldState(campaign_id=str(campaign_id))
        self.save_world_state(state)
        return state

    # =========================================================================
    # LOCATIONS
    # =========================================================================

    def get_location(self, campaign_id: str, location_id: str) -> Optional[SandboxLocation]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT campaign_id, location_id, parent_id, title, facts, discovered,
                       connected_locations_json, linked_dungeon_id, metadata_json
                FROM Sandbox_Locations
                WHERE campaign_id = ? AND location_id = ?
                """,
                (str(campaign_id), str(location_id)),
            ).fetchone()
        return self._row_to_location(row) if row else None

    def list_locations(
        self,
        campaign_id: str,
        parent_id: Optional[str] = None,
    ) -> List[SandboxLocation]:
        self.ensure_schema()
        if parent_id is not None:
            with self.db.get_db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT campaign_id, location_id, parent_id, title, facts, discovered,
                           connected_locations_json, linked_dungeon_id, metadata_json
                    FROM Sandbox_Locations
                    WHERE campaign_id = ? AND parent_id = ?
                    ORDER BY location_id
                    """,
                    (str(campaign_id), str(parent_id)),
                ).fetchall()
        else:
            with self.db.get_db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT campaign_id, location_id, parent_id, title, facts, discovered,
                           connected_locations_json, linked_dungeon_id, metadata_json
                    FROM Sandbox_Locations
                    WHERE campaign_id = ?
                    ORDER BY location_id
                    """,
                    (str(campaign_id),),
                ).fetchall()
        return [self._row_to_location(row) for row in rows]

    def save_location(self, location: SandboxLocation) -> None:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Sandbox_Locations (
                    campaign_id, location_id, parent_id, title, facts, discovered,
                    connected_locations_json, linked_dungeon_id, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(campaign_id, location_id)
                DO UPDATE SET
                    parent_id = excluded.parent_id,
                    title = excluded.title,
                    facts = excluded.facts,
                    discovered = excluded.discovered,
                    connected_locations_json = excluded.connected_locations_json,
                    linked_dungeon_id = excluded.linked_dungeon_id,
                    metadata_json = excluded.metadata_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    str(location.campaign_id),
                    str(location.location_id),
                    self._optional_str(location.parent_id),
                    str(location.title or ""),
                    str(location.facts or ""),
                    1 if location.discovered else 0,
                    self.db.safe_json_dump(list(location.connected_locations or [])),
                    self._optional_str(location.linked_dungeon_id),
                    self.db.safe_json_dump(dict(location.metadata or {})),
                ),
            )
            conn.commit()

    def mark_location_discovered(self, campaign_id: str, location_id: str) -> None:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                UPDATE Sandbox_Locations
                SET discovered = 1, updated_at = CURRENT_TIMESTAMP
                WHERE campaign_id = ? AND location_id = ?
                """,
                (str(campaign_id), str(location_id)),
            )
            conn.commit()

    # =========================================================================
    # NPCS
    # =========================================================================

    def get_npc(self, campaign_id: str, npc_id: str) -> Optional[SandboxNPC]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT campaign_id, npc_id, name, current_location_id,
                       relationships_json, memory_logs_json, metadata_json
                FROM Sandbox_NPCs
                WHERE campaign_id = ? AND npc_id = ?
                """,
                (str(campaign_id), str(npc_id)),
            ).fetchone()
        return self._row_to_npc(row) if row else None

    def list_npcs_at_location(self, campaign_id: str, location_id: str) -> List[SandboxNPC]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT campaign_id, npc_id, name, current_location_id,
                       relationships_json, memory_logs_json, metadata_json
                FROM Sandbox_NPCs
                WHERE campaign_id = ? AND current_location_id = ?
                ORDER BY npc_id
                """,
                (str(campaign_id), str(location_id)),
            ).fetchall()
        return [self._row_to_npc(row) for row in rows]

    def save_npc(self, npc: SandboxNPC) -> None:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Sandbox_NPCs (
                    campaign_id, npc_id, name, current_location_id,
                    relationships_json, memory_logs_json, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(campaign_id, npc_id)
                DO UPDATE SET
                    name = excluded.name,
                    current_location_id = excluded.current_location_id,
                    relationships_json = excluded.relationships_json,
                    memory_logs_json = excluded.memory_logs_json,
                    metadata_json = excluded.metadata_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    str(npc.campaign_id),
                    str(npc.npc_id),
                    str(npc.name or ""),
                    self._optional_str(npc.current_location_id),
                    self.db.safe_json_dump(
                        {str(k): int(v) for k, v in (npc.relationships or {}).items()}
                    ),
                    self.db.safe_json_dump(list(npc.memory_logs or [])),
                    self.db.safe_json_dump(dict(npc.metadata or {})),
                ),
            )
            conn.commit()

    def append_npc_memory(self, campaign_id: str, npc_id: str, memory_entry: str) -> None:
        self.ensure_schema()
        npc = self.get_npc(campaign_id, npc_id)
        if npc is None:
            npc = SandboxNPC(npc_id=str(npc_id), campaign_id=str(campaign_id))
        npc.memory_logs.append(str(memory_entry))
        self.save_npc(npc)

    def _list_all_npcs(self, campaign_id: str) -> List[SandboxNPC]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT campaign_id, npc_id, name, current_location_id,
                       relationships_json, memory_logs_json, metadata_json
                FROM Sandbox_NPCs
                WHERE campaign_id = ?
                ORDER BY npc_id
                """,
                (str(campaign_id),),
            ).fetchall()
        return [self._row_to_npc(row) for row in rows]

    # =========================================================================
    # FACTIONS
    # =========================================================================

    def get_faction(self, campaign_id: str, faction_id: str) -> Optional[SandboxFaction]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT campaign_id, faction_id, name, goals_json, dispositions_json, metadata_json
                FROM Sandbox_Factions
                WHERE campaign_id = ? AND faction_id = ?
                """,
                (str(campaign_id), str(faction_id)),
            ).fetchone()
        return self._row_to_faction(row) if row else None

    def list_factions(self, campaign_id: str) -> List[SandboxFaction]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT campaign_id, faction_id, name, goals_json, dispositions_json, metadata_json
                FROM Sandbox_Factions
                WHERE campaign_id = ?
                ORDER BY faction_id
                """,
                (str(campaign_id),),
            ).fetchall()
        return [self._row_to_faction(row) for row in rows]

    def save_faction(self, faction: SandboxFaction) -> None:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Sandbox_Factions (
                    campaign_id, faction_id, name, goals_json, dispositions_json, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(campaign_id, faction_id)
                DO UPDATE SET
                    name = excluded.name,
                    goals_json = excluded.goals_json,
                    dispositions_json = excluded.dispositions_json,
                    metadata_json = excluded.metadata_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    str(faction.campaign_id),
                    str(faction.faction_id),
                    str(faction.name or ""),
                    self.db.safe_json_dump(list(faction.goals or [])),
                    self.db.safe_json_dump(
                        {str(k): int(v) for k, v in (faction.dispositions or {}).items()}
                    ),
                    self.db.safe_json_dump(dict(faction.metadata or {})),
                ),
            )
            conn.commit()

    # =========================================================================
    # KNOWLEDGE FOG
    # =========================================================================

    def get_knowledge_fog(
        self,
        channel_id: str,
        player_id: str = "",
    ) -> Optional[SandboxKnowledgeFog]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT channel_id, player_id, discovered_location_ids_json,
                       known_npc_ids_json, known_faction_ids_json, revealed_facts_json
                FROM Sandbox_Knowledge_Fog
                WHERE channel_id = ? AND player_id = ?
                """,
                (str(channel_id), str(player_id or "")),
            ).fetchone()
        return self._row_to_knowledge_fog(row) if row else None

    def get_or_create_knowledge_fog(
        self,
        channel_id: str,
        player_id: str = "",
    ) -> SandboxKnowledgeFog:
        existing = self.get_knowledge_fog(channel_id, player_id)
        if existing is not None:
            return existing

        fog = SandboxKnowledgeFog(channel_id=str(channel_id), player_id=str(player_id or ""))
        self.update_knowledge_fog(fog)
        return fog

    def update_knowledge_fog(self, fog: SandboxKnowledgeFog) -> None:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Sandbox_Knowledge_Fog (
                    channel_id, player_id, discovered_location_ids_json,
                    known_npc_ids_json, known_faction_ids_json, revealed_facts_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id, player_id)
                DO UPDATE SET
                    discovered_location_ids_json = excluded.discovered_location_ids_json,
                    known_npc_ids_json = excluded.known_npc_ids_json,
                    known_faction_ids_json = excluded.known_faction_ids_json,
                    revealed_facts_json = excluded.revealed_facts_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    str(fog.channel_id),
                    str(fog.player_id or ""),
                    self.db.safe_json_dump(sorted(fog.discovered_location_ids)),
                    self.db.safe_json_dump(sorted(fog.known_npc_ids)),
                    self.db.safe_json_dump(sorted(fog.known_faction_ids)),
                    self.db.safe_json_dump(list(fog.revealed_facts or [])),
                ),
            )
            conn.commit()

    # =========================================================================
    # INTERNAL ROW <-> MODEL MAPPING HELPERS
    # =========================================================================

    def _row_to_location(self, row: Any) -> SandboxLocation:
        return SandboxLocation(
            location_id=str(row["location_id"]),
            campaign_id=str(row["campaign_id"]),
            parent_id=row["parent_id"],
            title=str(row["title"] or ""),
            facts=str(row["facts"] or ""),
            discovered=bool(row["discovered"]),
            connected_locations=[
                str(x) for x in self.db.safe_json_load(row["connected_locations_json"], [])
            ],
            linked_dungeon_id=row["linked_dungeon_id"],
            metadata=self.db.safe_json_load(row["metadata_json"], {}),
        )

    def _row_to_npc(self, row: Any) -> SandboxNPC:
        return SandboxNPC(
            npc_id=str(row["npc_id"]),
            campaign_id=str(row["campaign_id"]),
            name=str(row["name"] or ""),
            current_location_id=row["current_location_id"],
            relationships=self._int_dict(self.db.safe_json_load(row["relationships_json"], {})),
            memory_logs=[str(x) for x in self.db.safe_json_load(row["memory_logs_json"], [])],
            metadata=self.db.safe_json_load(row["metadata_json"], {}),
        )

    def _row_to_faction(self, row: Any) -> SandboxFaction:
        return SandboxFaction(
            faction_id=str(row["faction_id"]),
            campaign_id=str(row["campaign_id"]),
            name=str(row["name"] or ""),
            goals=[str(x) for x in self.db.safe_json_load(row["goals_json"], [])],
            dispositions=self._int_dict(self.db.safe_json_load(row["dispositions_json"], {})),
            metadata=self.db.safe_json_load(row["metadata_json"], {}),
        )

    def _row_to_knowledge_fog(self, row: Any) -> SandboxKnowledgeFog:
        return SandboxKnowledgeFog(
            channel_id=str(row["channel_id"]),
            player_id=str(row["player_id"] or ""),
            discovered_location_ids={
                str(x) for x in self.db.safe_json_load(row["discovered_location_ids_json"], [])
            },
            known_npc_ids={
                str(x) for x in self.db.safe_json_load(row["known_npc_ids_json"], [])
            },
            known_faction_ids={
                str(x) for x in self.db.safe_json_load(row["known_faction_ids_json"], [])
            },
            revealed_facts=[
                str(x) for x in self.db.safe_json_load(row["revealed_facts_json"], [])
            ],
        )

    @staticmethod
    def _optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _int_dict(value: Dict[str, Any]) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for key, raw in (value or {}).items():
            try:
                result[str(key)] = int(raw)
            except (TypeError, ValueError):
                continue
        return result
