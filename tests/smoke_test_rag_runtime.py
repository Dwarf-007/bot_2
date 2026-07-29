"""
Optional smoke test for lightweight RAG runtime.
Run:
    python tests/smoke_test_rag_runtime.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    runtime.rag_chunk_repo.upsert_chunk({
        "chunk_id": "rag_test_1",
        "campaign_id": "default",
        "room_id": "room_crypt",
        "source": "smoke_test",
        "text": "A kripta közepén egy ősi kőszarkofág áll. A fedelén hold motívum látható.",
        "metadata": {"page": 1},
    })
    runtime.rag_chunk_repo.upsert_chunk({
        "chunk_id": "rag_test_2",
        "campaign_id": "default",
        "room_id": "room_forest",
        "source": "smoke_test",
        "text": "A sűrű erdőben farkasnyomok vezetnek észak felé.",
        "metadata": {"page": 2},
    })
    results = runtime.rag_runtime.search("ősi szarkofág kripta", top_k=3, campaign_id="default")
    print(results)


if __name__ == "__main__":
    main()
