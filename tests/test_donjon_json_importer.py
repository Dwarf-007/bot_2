"""
Sprint 1 smoke/unit test for DonjonJsonImporter.
Run:
    python tests/test_donjon_json_importer.py
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.donjon.donjon_json_importer import DonjonJsonImporter


def cell(room_id: int, room: bool = False, corridor: bool = False, door: bool = False, arch: bool = False, locked: bool = False, trapped: bool = False, secret: bool = False) -> int:
    bits = DonjonJsonImporter.DEFAULT_BITS
    value = 0
    if room:
        value |= bits["room"] | (room_id << 6)
    if corridor:
        value |= bits["corridor"]
    if door:
        value |= bits["door"] | bits["corridor"]
    if arch:
        value |= bits["arch"] | bits["corridor"]
    if locked:
        value |= bits["locked"]
    if trapped:
        value |= bits["trapped"]
    if secret:
        value |= bits["secret"] | bits["corridor"]
    return value


def build_fixture() -> dict:
    # Two 2x2 rooms connected by a trapped/locked door and a short corridor.
    # Grid legend:
    # R R D . R R
    # R R c c R R
    cells = [
        [cell(1, room=True), cell(1, room=True), cell(0, door=True, locked=True, trapped=True), cell(0), cell(2, room=True), cell(2, room=True)],
        [cell(1, room=True), cell(1, room=True), cell(0, corridor=True), cell(0, corridor=True), cell(2, room=True), cell(2, room=True)],
    ]
    return {"title": "Fixture Dungeon", "cell_bit": DonjonJsonImporter.DEFAULT_BITS, "cells": cells}


def main() -> None:
    importer = DonjonJsonImporter()
    dungeon = importer.import_data(build_fixture(), dungeon_id="fixture", title="Fixture Dungeon")
    assert dungeon.dungeon_id == "fixture"
    assert dungeon.width == 6
    assert dungeon.height == 2
    assert len(dungeon.rooms) == 2, dungeon.summary()
    assert len(dungeon.doors) >= 1, dungeon.summary()
    assert len(dungeon.traps) >= 1, dungeon.summary()
    assert any({connection.from_room_id, connection.to_room_id} == {"1", "2"} for connection in dungeon.connections), dungeon.to_dict()
    print("OK", dungeon.summary())


if __name__ == "__main__":
    main()
