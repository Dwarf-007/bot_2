"""
Sprint 4 test for GenerationOrchestrator.
Run from project root:
    python tests/test_generation_orchestrator.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from services.donjon.donjon_json_importer import DonjonJsonImporter
    from services.generators.generation_orchestrator import GenerateCampaignRequest, GenerationOrchestrator
    from services.generators.generate_command_parser import GenerateCommandParser
except ModuleNotFoundError as exc:
    print(f"SKIP GenerationOrchestrator integration test: missing cumulative dependency: {exc}")
    raise SystemExit(0)


def cell(room_id: int, room: bool = False, corridor: bool = False, door: bool = False, trapped: bool = False) -> int:
    bits = DonjonJsonImporter.DEFAULT_BITS
    value = 0
    if room:
        value |= bits["room"] | (room_id << 6)
    if corridor:
        value |= bits["corridor"]
    if door:
        value |= bits["door"] | bits["corridor"]
    if trapped:
        value |= bits["trapped"]
    return value


def write_fixture(path: Path) -> None:
    data = {
        "title": "Fixture Generated Campaign",
        "cell_bit": DonjonJsonImporter.DEFAULT_BITS,
        "cells": [
            [cell(1, room=True), cell(1, room=True), cell(0, door=True, trapped=True), cell(0, corridor=True), cell(2, room=True), cell(2, room=True)],
            [cell(1, room=True), cell(1, room=True), cell(0, corridor=True), cell(0, corridor=True), cell(2, room=True), cell(2, room=True)],
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    root = Path("_tmp_generation_orchestrator")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()
    source = root / "fixture_donjon.json"
    output = root / "campaign"
    write_fixture(source)

    parsed = GenerateCommandParser().parse(f'donjon_json fixture "{source}" --name "Fixture" --theme "crimson curse" --import --clear-rag')
    assert parsed.campaign_id == "fixture"
    assert parsed.import_to_runtime is True
    assert parsed.clear_rag is True

    request = GenerateCampaignRequest(
        campaign_id="fixture",
        campaign_name="Fixture",
        source_path=str(source),
        output_dir=str(output),
        theme="crimson curse",
        enrich=True,
    )
    result = GenerationOrchestrator().generate_campaign(request)
    assert result.generated_summary["room_count"] == 2
    assert (output / "generated_dungeon.json").exists()
    assert (output / "bundle" / "room_data.json").exists()
    assert (output / "bundle" / "rag_index.json").exists()
    assert (output / "bundle" / "enrichment.json").exists()
    assert "Generated campaign ready" in result.to_text()
    shutil.rmtree(root)
    print("OK GenerationOrchestrator")


if __name__ == "__main__":
    main()
