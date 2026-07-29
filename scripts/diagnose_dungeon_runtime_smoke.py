#!/usr/bin/env python3
"""Diagnose a Dungeon Runtime MVP smoke JSON result."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.dungeon_runtime_smoke_diagnostics import DungeonRuntimeSmokeDiagnostics


def parse_args():
    parser = argparse.ArgumentParser(description="Diagnose Dungeon Runtime MVP smoke result JSON.")
    parser.add_argument("json_file", help="Path to smoke_runtime_mvp_result.json")
    parser.add_argument("--json-out", default="", help="Optional output path for structured diagnosis JSON")
    parser.add_argument("--fail-on-false-green", action="store_true", help="Return exit code 2 when false green is detected")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    diagnosis = DungeonRuntimeSmokeDiagnostics().diagnose_file(args.json_file)
    print(diagnosis.summary_text())
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(diagnosis.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Diagnosis JSON written: {out}")
    if args.fail_on_false_green and diagnosis.false_green:
        return 2
    return 0 if diagnosis.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
