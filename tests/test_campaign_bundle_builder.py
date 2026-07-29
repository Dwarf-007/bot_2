"""
Sprint 2 test for CampaignBundleBuilder.
Run from project root:
    python tests/test_campaign_bundle_builder.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.generators.campaign_bundle_builder import CampaignBundleBuilder


def fixture_generated_dungeon() -> dict:
    return {
        "dungeon_id": "fixture",
        "title": "Fixture Dungeon",
        "source": "donjon_json",
        "width": 6,
        "height": 2,
        "rooms": [
            {"room_id": "1", "title": "Room #1", "x": 0, "y": 0, "width": 2, "height": 2, "cells": [(0, 0), (1, 0), (0, 1), (1, 1)], "metadata": {}},
            {"room_id": "2", "title": "Room #2", "x": 4, "y": 0, "width": 2, "height": 2, "cells": [(4, 0), (5, 0), (4, 1), (5, 1)], "metadata": {}},
        ],
        "connections": [
            {"from_room_id": "1", "to_room_id": "2", "direction": "east", "via": "door", "door_ids": ["door_0001"], "distance": 3, "locked": True, "trapped": True, "secret": False}
        ],
        "doors": [
            {"door_id": "door_0001", "x": 2, "y": 0, "kind": "door", "locked": True, "trapped": True, "secret": False, "metadata": {}}
        ],
        "traps": [
            {"trap_id": "trap_0001", "x": 2, "y": 0, "kind": "door_trap", "description": "Trapped door", "metadata": {"door_id": "door_0001"}}
        ],
        "metadata": {},
    }


def main() -> None:
    output_dir = Path("_tmp_campaign_bundle_test")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    builder = CampaignBundleBuilder()
    outputs = builder.write_bundle(fixture_generated_dungeon(), campaign_id="fixture", output_dir=output_dir, campaign_name="Fixture Dungeon")

    for key in ["room_data", "room_lookup", "rag_index", "toc_index", "manifest"]:
        assert Path(outputs[key]).exists(), outputs

    room_data = json.loads(Path(outputs["room_data"]).read_text(encoding="utf-8"))
    room_lookup = json.loads(Path(outputs["room_lookup"]).read_text(encoding="utf-8"))
    rag_index = json.loads(Path(outputs["rag_index"]).read_text(encoding="utf-8"))
    toc_index = json.loads(Path(outputs["toc_index"]).read_text(encoding="utf-8"))

    assert len(room_data["rooms"]) == 2
    assert room_data["rooms"][0]["exits"].get("east") == "2"
    assert "room #1" in room_lookup
    assert len(rag_index["chunks"]) == 2
    assert len(toc_index["entries"]) == 2
    assert "trapped" in room_data["rooms"][0]["facts"]

    shutil.rmtree(output_dir)
    print("OK CampaignBundleBuilder")


if __name__ == "__main__":
    main()
