#!/usr/bin/env python3
"""Audit Dungeon Runtime path_history in a visibility runtime state JSON file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.dungeon_runtime_path_history_auditor import DungeonRuntimePathHistoryAuditor


def parse_args():
    parser = argparse.ArgumentParser(description="Audit Dungeon Runtime path_history semantics.")
    parser.add_argument("--state-file", required=True, help="Path to visibility_runtime_state_<channel>.json")
    parser.add_argument("--json-out", default="", help="Optional structured JSON output path")
    parser.add_argument("--fail-on-warn", action="store_true", help="Return exit code 2 when audit status is WARN")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = DungeonRuntimePathHistoryAuditor().audit_file(args.state_file)
    print(result.summary_text())
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Path history audit JSON written: {out}")
    if result.status == "FAIL":
        return 1
    if args.fail_on_warn and result.status == "WARN":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
