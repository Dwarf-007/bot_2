#!/usr/bin/env python3
"""Validate Dungeon Runtime FOW state after smoke."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.dungeon_runtime_fow_validator import DungeonRuntimeFowValidator


def parse_args():
    parser = argparse.ArgumentParser(description="Validate Dungeon Runtime FOW state file.")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--campaign-id", default="")
    parser.add_argument("--channel-id", default="")
    parser.add_argument("--allow-empty-visible", action="store_true")
    parser.add_argument("--require-current-cell-when-segment", action="store_true")
    parser.add_argument("--json-out", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = DungeonRuntimeFowValidator().validate_state_file(
        state_file=args.state_file,
        campaign_id=args.campaign_id,
        channel_id=args.channel_id,
        require_visible_cells=not args.allow_empty_visible,
        require_current_cell_when_segment=args.require_current_cell_when_segment,
    )
    print(result.summary_text())
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"FOW validation JSON written: {out}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
