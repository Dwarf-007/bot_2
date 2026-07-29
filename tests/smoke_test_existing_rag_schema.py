"""
Optional smoke test for existing rag_chunks + rag_chunks_fts schema.
Run:
    python tests/smoke_test_existing_rag_schema.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    campaign_id = "MoG_TEST"
    runtime.rag_chunk_repo.delete_campaign_chunks(campaign_id)
    runtime.rag_chunk_repo.upsert_chunk({
        "campaign_id": campaign_id,
        "chunk_id": "1",
        "room_id": "graymoor_bend_01",
        "title": "Graymoor Bend",
        "text": "George Gilly lies face down in the snow outside the Graymoor Bend Inn.",
        "tags": ["location", "murder"],
        "npc_names": ["George Gilly"],
        "monster_names": [],
        "trap_names": [],
        "keyword_hits": ["snow", "murder"],
    })
    results = runtime.rag_runtime.search("George Gilly snow", top_k=3, campaign_id=campaign_id)
    print(results)


if __name__ == "__main__":
    main()
