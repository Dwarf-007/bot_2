#!/usr/bin/env python3
"""Run the C5 Combat Runtime smoke service.

This script is intentionally dependency-light:
- no Discord connection
- no Avrae runtime
- no database
- no real LLM provider

It runs the deterministic CombatRuntimeSmokeService introduced in C5.1 and can
optionally write a JSON result for CI/manual audit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Allow running directly from repository root or from scripts/.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.combat_runtime_smoke_service import CombatRuntimeSmokeService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Combat Runtime smoke service.")
    parser.add_argument(
        "--channel-id",
        default="combat-smoke-channel",
        help="Channel id used by the in-memory smoke state.",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional path where the structured smoke result JSON should be written.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the final OK/FAIL line.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = CombatRuntimeSmokeService().run(channel_id=str(args.channel_id))

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        if not args.quiet:
            print(f"Combat Runtime smoke JSON written: {out}")

    if args.quiet:
        print("OK" if result.ok else "FAIL")
    else:
        print(result.summary_text())

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
