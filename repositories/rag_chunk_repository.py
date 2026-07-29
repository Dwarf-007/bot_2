"""
REPOSITORIES/RAG_CHUNK_REPOSITORY.PY
Compatibility repository for the generated existing RAG schema.

Expected schema handled by this repository:

CREATE TABLE rag_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    room_id TEXT,
    title TEXT,
    text TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    npc_names_json TEXT NOT NULL,
    monster_names_json TEXT NOT NULL,
    trap_names_json TEXT NOT NULL,
    keyword_hits_json TEXT NOT NULL,
    embedding BLOB
)

CREATE VIRTUAL TABLE rag_chunks_fts
USING fts5(title, text, tags, keyword_hits)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from models.rag_chunk import RagChunkRecord, RagSearchResult
from repositories.base import BaseRepository


class RagChunkRepository(BaseRepository):
    def ensure_schema(self) -> None:
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    room_id TEXT,
                    title TEXT,
                    text TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    npc_names_json TEXT NOT NULL,
                    monster_names_json TEXT NOT NULL,
                    trap_names_json TEXT NOT NULL,
                    keyword_hits_json TEXT NOT NULL,
                    embedding BLOB
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_rag_campaign_chunk
                ON rag_chunks(campaign_id, chunk_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_rag_campaign_room
                ON rag_chunks(campaign_id, room_id)
                """
            )
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts
                USING fts5(title, text, tags, keyword_hits)
                """
            )
            conn.commit()

    def upsert_chunk(self, chunk: Dict[str, Any]) -> int:
        self.ensure_schema()
        normalized = self._normalize_chunk(chunk)

        with self.db.get_db_connection() as conn:
            existing = conn.execute(
                """
                SELECT id FROM rag_chunks
                WHERE campaign_id = ? AND chunk_id = ?
                """,
                (normalized["campaign_id"], normalized["chunk_id"]),
            ).fetchall()
            for row in existing:
                conn.execute("DELETE FROM rag_chunks_fts WHERE rowid = ?", (int(row["id"]),))
            conn.execute(
                "DELETE FROM rag_chunks WHERE campaign_id = ? AND chunk_id = ?",
                (normalized["campaign_id"], normalized["chunk_id"]),
            )

            cursor = conn.execute(
                """
                INSERT INTO rag_chunks (
                    campaign_id, chunk_id, room_id, title, text,
                    tags_json, npc_names_json, monster_names_json,
                    trap_names_json, keyword_hits_json, embedding
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized["campaign_id"],
                    normalized["chunk_id"],
                    normalized["room_id"],
                    normalized["title"],
                    normalized["text"],
                    self.db.safe_json_dump(normalized["tags"]),
                    self.db.safe_json_dump(normalized["npc_names"]),
                    self.db.safe_json_dump(normalized["monster_names"]),
                    self.db.safe_json_dump(normalized["trap_names"]),
                    self.db.safe_json_dump(normalized["keyword_hits"]),
                    normalized.get("embedding"),
                ),
            )
            row_id = int(cursor.lastrowid)
            conn.execute(
                """
                INSERT INTO rag_chunks_fts (rowid, title, text, tags, keyword_hits)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    normalized["title"] or "",
                    normalized["text"],
                    " ".join(normalized["tags"]),
                    " ".join(normalized["keyword_hits"]),
                ),
            )
            conn.commit()
            return row_id

    def get_chunk(self, campaign_id: str, chunk_id: str) -> Optional[RagChunkRecord]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM rag_chunks
                WHERE campaign_id = ? AND chunk_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (str(campaign_id), str(chunk_id)),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def list_chunks(
        self,
        campaign_id: Optional[str] = None,
        room_id: Optional[str] = None,
        limit: int = 1000,
    ) -> List[RagChunkRecord]:
        self.ensure_schema()
        safe_limit = max(1, min(int(limit or 1000), 10000))
        clauses: list[str] = []
        params: list[Any] = []
        if campaign_id:
            clauses.append("campaign_id = ?")
            params.append(str(campaign_id))
        if room_id:
            clauses.append("room_id = ?")
            params.append(str(room_id))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(safe_limit)
        with self.db.get_db_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM rag_chunks
                {where}
                ORDER BY id
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def search_fts(
        self,
        query: str,
        campaign_id: str,
        room_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[RagSearchResult]:
        self.ensure_schema()
        fts_query = self._to_fts_query(query)
        if not fts_query:
            return []
        safe_limit = max(1, min(int(limit or 5), 50))

        clauses = ["c.campaign_id = ?"]
        params: list[Any] = [fts_query, str(campaign_id)]
        if room_id:
            clauses.append("c.room_id = ?")
            params.append(str(room_id))
        where = " AND ".join(clauses)
        params.append(safe_limit)

        try:
            with self.db.get_db_connection() as conn:
                rows = conn.execute(
                    f"""
                    SELECT
                        c.*,
                        bm25(rag_chunks_fts) AS rank_score
                    FROM rag_chunks_fts
                    JOIN rag_chunks c ON rag_chunks_fts.rowid = c.id
                    WHERE rag_chunks_fts MATCH ?
                      AND {where}
                    ORDER BY rank_score ASC
                    LIMIT ?
                    """,
                    tuple(params),
                ).fetchall()
        except Exception:
            return []

        results: List[RagSearchResult] = []
        for row in rows:
            record = self._row_to_record(row)
            raw_rank = float(row["rank_score"] if row["rank_score"] is not None else 0.0)
            # bm25 lower is better; convert to positive-ish score for uniform API.
            score = round(1.0 / (1.0 + abs(raw_rank)), 6)
            results.append(self._record_to_search_result(record, score))
        return results

    def delete_campaign_chunks(self, campaign_id: str) -> int:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            rows = conn.execute(
                "SELECT id FROM rag_chunks WHERE campaign_id = ?",
                (str(campaign_id),),
            ).fetchall()
            for row in rows:
                conn.execute("DELETE FROM rag_chunks_fts WHERE rowid = ?", (int(row["id"]),))
            cursor = conn.execute("DELETE FROM rag_chunks WHERE campaign_id = ?", (str(campaign_id),))
            conn.commit()
            return int(cursor.rowcount or 0)

    def rebuild_fts(self, campaign_id: Optional[str] = None) -> int:
        self.ensure_schema()
        chunks = self.list_chunks(campaign_id=campaign_id, limit=10000)
        with self.db.get_db_connection() as conn:
            if campaign_id:
                ids = [chunk.id for chunk in chunks if chunk.id is not None]
                for row_id in ids:
                    conn.execute("DELETE FROM rag_chunks_fts WHERE rowid = ?", (row_id,))
            else:
                conn.execute("DELETE FROM rag_chunks_fts")
            for chunk in chunks:
                conn.execute(
                    """
                    INSERT INTO rag_chunks_fts (rowid, title, text, tags, keyword_hits)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.id,
                        chunk.title or "",
                        chunk.text,
                        " ".join(chunk.tags),
                        " ".join(chunk.keyword_hits),
                    ),
                )
            conn.commit()
        return len(chunks)

    def _row_to_record(self, row) -> RagChunkRecord:
        return RagChunkRecord(
            id=int(row["id"]) if row["id"] is not None else None,
            campaign_id=str(row["campaign_id"]),
            chunk_id=str(row["chunk_id"]),
            room_id=self._optional_str(row["room_id"]),
            title=self._optional_str(row["title"]),
            text=str(row["text"]),
            tags=self.db.safe_json_load(row["tags_json"], []),
            npc_names=self.db.safe_json_load(row["npc_names_json"], []),
            monster_names=self.db.safe_json_load(row["monster_names_json"], []),
            trap_names=self.db.safe_json_load(row["trap_names_json"], []),
            keyword_hits=self.db.safe_json_load(row["keyword_hits_json"], []),
            embedding=row["embedding"] if "embedding" in row.keys() else None,
        )

    @staticmethod
    def _record_to_search_result(record: RagChunkRecord, score: float) -> RagSearchResult:
        return RagSearchResult(
            id=record.id,
            campaign_id=record.campaign_id,
            chunk_id=record.chunk_id,
            room_id=record.room_id,
            title=record.title,
            text=record.text,
            tags=record.tags,
            npc_names=record.npc_names,
            monster_names=record.monster_names,
            trap_names=record.trap_names,
            keyword_hits=record.keyword_hits,
            score=score,
        )

    @staticmethod
    def _normalize_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
        chunk_id = str(chunk.get("chunk_id") or chunk.get("id") or "").strip()
        if not chunk_id:
            raise ValueError("chunk_id is required")
        text = str(chunk.get("text") or chunk.get("chunk_text") or "").strip()
        if not text:
            raise ValueError("chunk text is required")
        return {
            "campaign_id": str(chunk.get("campaign_id") or "default"),
            "chunk_id": chunk_id,
            "room_id": RagChunkRepository._optional_str(chunk.get("room_id")),
            "title": RagChunkRepository._optional_str(chunk.get("title")),
            "text": text,
            "tags": RagChunkRepository._list_of_str(chunk.get("tags")),
            "npc_names": RagChunkRepository._list_of_str(chunk.get("npc_names")),
            "monster_names": RagChunkRepository._list_of_str(chunk.get("monster_names")),
            "trap_names": RagChunkRepository._list_of_str(chunk.get("trap_names")),
            "keyword_hits": RagChunkRepository._list_of_str(chunk.get("keyword_hits")),
            "embedding": chunk.get("embedding"),
        }

    @staticmethod
    def _to_fts_query(query: str) -> str:
        terms = re.findall(r"[0-9a-zA-ZáéíóöőúüűÁÉÍÓÖŐÚÜŰ]{2,}", str(query or "").lower())
        terms = [term for term in terms[:12] if term not in {"the", "and", "egy", "van", "hogy", "room", "szoba"}]
        return " OR ".join(terms)

    @staticmethod
    def _optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _list_of_str(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]
