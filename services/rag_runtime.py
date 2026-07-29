"""
SERVICES/RAG_RUNTIME.PY
RAG runtime compatible with the existing generated rag_chunks + rag_chunks_fts schema.

Search order:
1. SQLite FTS5 if available and returning results.
2. Fallback lexical scorer over rag_chunks rows.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from models.rag_chunk import RagChunkRecord, RagSearchResult


class ExistingSchemaRagRuntime:
    def __init__(self, rag_repo, default_campaign_id: str = "default") -> None:
        self.rag_repo = rag_repo
        self.default_campaign_id = default_campaign_id
        self.rag_repo.ensure_schema()

    def search(
        self,
        query: str,
        top_k: int = 5,
        campaign_id: Optional[str] = None,
        room_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        records = self.search_records(query, top_k=top_k, campaign_id=campaign_id, room_id=room_id)
        return [self._result_to_dict(item) for item in records]

    def search_records(
        self,
        query: str,
        top_k: int = 5,
        campaign_id: Optional[str] = None,
        room_id: Optional[str] = None,
    ) -> List[RagSearchResult]:
        safe_top_k = max(1, min(int(top_k or 5), 20))
        active_campaign = campaign_id or self.default_campaign_id

        fts_results = self.rag_repo.search_fts(
            query=query,
            campaign_id=active_campaign,
            room_id=room_id,
            limit=safe_top_k,
        )
        if fts_results:
            return fts_results

        return self._fallback_lexical_search(
            query=query,
            top_k=safe_top_k,
            campaign_id=active_campaign,
            room_id=room_id,
        )

    def _fallback_lexical_search(
        self,
        query: str,
        top_k: int,
        campaign_id: str,
        room_id: Optional[str],
    ) -> List[RagSearchResult]:
        query_terms = self._terms(query)
        if not query_terms:
            return []

        chunks = self.rag_repo.list_chunks(campaign_id=campaign_id, room_id=room_id, limit=10000)
        if room_id and not chunks:
            chunks = self.rag_repo.list_chunks(campaign_id=campaign_id, limit=10000)

        results: List[RagSearchResult] = []
        for chunk in chunks:
            score = self._score(query_terms, chunk)
            if score <= 0:
                continue
            results.append(
                RagSearchResult(
                    id=chunk.id,
                    campaign_id=chunk.campaign_id,
                    chunk_id=chunk.chunk_id,
                    room_id=chunk.room_id,
                    title=chunk.title,
                    text=chunk.text,
                    tags=chunk.tags,
                    npc_names=chunk.npc_names,
                    monster_names=chunk.monster_names,
                    trap_names=chunk.trap_names,
                    keyword_hits=chunk.keyword_hits,
                    score=score,
                )
            )
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    def _score(self, query_terms: List[str], chunk: RagChunkRecord) -> float:
        weighted_text = " ".join(
            [
                chunk.title or "",
                chunk.text,
                " ".join(chunk.tags),
                " ".join(chunk.npc_names),
                " ".join(chunk.monster_names),
                " ".join(chunk.trap_names),
                " ".join(chunk.keyword_hits),
            ]
        )
        doc_terms = self._terms(weighted_text)
        if not doc_terms:
            return 0.0
        q_counts = Counter(query_terms)
        d_counts = Counter(doc_terms)
        overlap = sum(min(q_counts[term], d_counts.get(term, 0)) for term in q_counts)
        if overlap <= 0:
            return 0.0
        score = overlap / math.sqrt(max(1, len(doc_terms)))
        if chunk.room_id:
            score += 0.05
        if chunk.title:
            score += 0.03
        return round(score, 6)

    @staticmethod
    def _terms(text: str) -> List[str]:
        tokens = re.findall(r"[0-9a-zA-ZáéíóöőúüűÁÉÍÓÖŐÚÜŰ]{2,}", str(text or "").lower())
        stop_words = {
            "the", "and", "that", "with", "this", "from", "into", "room",
            "egy", "van", "hogy", "mint", "vagy", "azon", "ezek", "ahol", "szoba",
        }
        return [token for token in tokens if token not in stop_words]

    @staticmethod
    def _result_to_dict(item: RagSearchResult) -> Dict[str, Any]:
        return {
            "id": item.id,
            "chunk_id": item.chunk_id,
            "campaign_id": item.campaign_id,
            "room_id": item.room_id,
            "title": item.title,
            "score": item.score,
            "text": item.text,
            "tags": item.tags,
            "npc_names": item.npc_names,
            "monster_names": item.monster_names,
            "trap_names": item.trap_names,
            "keyword_hits": item.keyword_hits,
        }


# Backward-compatible alias used by refactor 14 bootstrap naming.
LightweightRagRuntime = ExistingSchemaRagRuntime
