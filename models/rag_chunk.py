"""
MODELS/RAG_CHUNK.PY
Typed DTOs for the existing generated RAG schema.

Compatible with generated rag_index.json and SQLite tables:
- rag_chunks
- rag_chunks_fts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RagChunkRecord:
    id: Optional[int]
    campaign_id: str
    chunk_id: str
    text: str
    room_id: Optional[str] = None
    title: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    npc_names: List[str] = field(default_factory=list)
    monster_names: List[str] = field(default_factory=list)
    trap_names: List[str] = field(default_factory=list)
    keyword_hits: List[str] = field(default_factory=list)
    embedding: Optional[bytes] = None


@dataclass(frozen=True)
class RagSearchResult:
    chunk_id: str
    campaign_id: str
    text: str
    score: float
    id: Optional[int] = None
    room_id: Optional[str] = None
    title: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    npc_names: List[str] = field(default_factory=list)
    monster_names: List[str] = field(default_factory=list)
    trap_names: List[str] = field(default_factory=list)
    keyword_hits: List[str] = field(default_factory=list)
