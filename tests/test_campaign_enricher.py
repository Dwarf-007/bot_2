"""
Sprint 3 test for CampaignEnricher.
Run from project root:
    python tests/test_campaign_enricher.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.generators.campaign_enricher import CampaignEnricher


def build_fixture_bundle(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    room_data = {
        "rooms": [
            {
                "campaign_id": "fixture",
                "room_id": "1",
                "title": "Room #1",
                "room_slug": "room_1",
                "facts": "Room #1.\nExits: east → room 2.",
                "exits": {"east": "2"},
                "monsters": [],
                "traps": [{"kind": "door_trap", "x": 2, "y": 0}],
                "treasures": [],
                "features": [],
                "source_chunk_ids": ["fixture_room_1"],
                "raw": {},
            },
            {
                "campaign_id": "fixture",
                "room_id": "2",
                "title": "Room #2",
                "room_slug": "room_2",
                "facts": "Room #2.\nExits: west → room 1.",
                "exits": {"west": "1"},
                "monsters": [],
                "traps": [],
                "treasures": [],
                "features": [],
                "source_chunk_ids": ["fixture_room_2"],
                "raw": {},
            },
        ]
    }
    rag_index = {"campaign_id": "fixture", "chunks": []}
    toc_index = {"campaign_id": "fixture", "entries": []}
    room_lookup = {"room #1": {"room_id": "1", "title": "Room #1", "slug": "room_1"}}
    (root / "room_data.json").write_text(json.dumps(room_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "rag_index.json").write_text(json.dumps(rag_index, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "toc_index.json").write_text(json.dumps(toc_index, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "room_lookup.json").write_text(json.dumps(room_lookup, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    input_dir = Path("_tmp_enricher_input")
    output_dir = Path("_tmp_enricher_output")
    for path in [input_dir, output_dir]:
        if path.exists():
            shutil.rmtree(path)
    build_fixture_bundle(input_dir)
    outputs = CampaignEnricher().write_enriched_bundle(
        input_dir=input_dir,
        output_dir=output_dir,
        campaign_id="fixture",
        campaign_name="Fixture Dungeon",
        theme="crimson lich curse",
    )
    for key in ["enrichment", "room_data", "room_lookup", "rag_index", "toc_index"]:
        assert Path(outputs[key]).exists(), outputs
    enriched_room_data = json.loads(Path(outputs["room_data"]).read_text(encoding="utf-8"))
    enriched_rag = json.loads(Path(outputs["rag_index"]).read_text(encoding="utf-8"))
    assert "Enrichment:" in enriched_room_data["rooms"][0]["facts"]
    assert enriched_room_data["rooms"][0]["raw"].get("enrichment")
    assert len(enriched_rag["chunks"]) >= 3
    shutil.rmtree(input_dir)
    shutil.rmtree(output_dir)
    print("OK CampaignEnricher")


if __name__ == "__main__":
    main()
