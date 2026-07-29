
"""
REPOSITORIES/CAMPAIGN_REPOSITORY.PY
Persistence abstraction for campaign registry.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.campaign import CampaignRecord
from repositories.base import BaseRepository


class CampaignRepository(BaseRepository):
    # Expected columns -> SQL type used when adding a missing column via migration.
    _CAMPAIGNS_COLUMNS: Dict[str, str] = {
        "campaign_id": "TEXT PRIMARY KEY",
        "name": "TEXT NOT NULL",
        "description": "TEXT NOT NULL DEFAULT ''",
        "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
        "party_size": "INTEGER",
        "party_level": "INTEGER",
        "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
    }

    def ensure_schema(self) -> None:
        with self.db.get_db_connection() as conn:
            # Create the table on first run with the full, current schema.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS Campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    party_size INTEGER,
                    party_level INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            # Idempotent migration: add any columns missing from an older schema.
            # CREATE TABLE IF NOT EXISTS is a no-op when the table already exists,
            # so a pre-existing table with a stale schema would otherwise lack
            # newer columns (e.g. party_size / party_level).
            existing = {row[1] for row in conn.execute("PRAGMA table_info(Campaigns)").fetchall()}
            for column, definition in self._CAMPAIGNS_COLUMNS.items():
                if column not in existing:
                    conn.execute(f"ALTER TABLE Campaigns ADD COLUMN {column} {definition}")
            conn.commit()

    def upsert_campaign(
        self,
        campaign_id: str,
        name: Optional[str] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        party_size: Optional[int] = None,
        party_level: Optional[int] = None,
    ) -> None:
        self.ensure_schema()
        cid = str(campaign_id or "").strip()
        if not cid:
            raise ValueError("campaign_id is required")
        display_name = str(name or cid)
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Campaigns (campaign_id, name, description, metadata_json, party_size, party_level)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(campaign_id)
                DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    metadata_json = excluded.metadata_json,
                    party_size = COALESCE(excluded.party_size, Campaigns.party_size),
                    party_level = COALESCE(excluded.party_level, Campaigns.party_level),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (cid, display_name, str(description or ""), self.db.safe_json_dump(metadata or {}), party_size, party_level),
            )
            conn.commit()

    def get_campaign(self, campaign_id: str) -> Optional[CampaignRecord]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT campaign_id, name, description, metadata_json, party_size, party_level, created_at, updated_at
                FROM Campaigns
                WHERE campaign_id = ?
                """,
                (str(campaign_id),),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def list_campaigns(self) -> List[CampaignRecord]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT campaign_id, name, description, metadata_json, party_size, party_level, created_at, updated_at
                FROM Campaigns
                ORDER BY campaign_id
                """
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def delete_campaign(self, campaign_id: str) -> None:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            conn.execute("DELETE FROM Campaigns WHERE campaign_id = ?", (str(campaign_id),))
            conn.commit()

    def _row_to_record(self, row) -> CampaignRecord:
        return CampaignRecord(
            campaign_id=str(row["campaign_id"]),
            name=str(row["name"]),
            description=str(row["description"] or ""),
            metadata=self.db.safe_json_load(row["metadata_json"], {}),
            party_size=row["party_size"],
            party_level=row["party_level"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
