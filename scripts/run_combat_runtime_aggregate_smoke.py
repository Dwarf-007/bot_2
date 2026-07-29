#!/usr/bin/env python3
"""Run the C5 Combat Runtime aggregate smoke gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.combat_runtime_aggregate_smoke_gate import CombatRuntimeAggregateSmokeGate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Combat Runtime aggregate smoke gate.")
    parser.add_argument("--channel-id", default="combat-aggregate-smoke")
    parser.add_argument("--json-out", default="")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = CombatRuntimeAggregateSmokeGate(project_root=PROJECT_ROOT).run(channel_id=str(args.channel_id))

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        if not args.quiet:
            print(f"Combat Runtime aggregate smoke JSON written: {out}")

    if args.quiet:
        print("OK" if result.ok else "FAIL")
    else:
        print(result.summary_text())

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
