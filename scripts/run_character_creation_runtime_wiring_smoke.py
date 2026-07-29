#!/usr/bin/env python3
"""Run the F2 CharacterCreationAdvisor runtime wiring smoke."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.compendium.character_creation_runtime_wiring_smoke import CharacterCreationRuntimeWiringSmoke


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run F2 CharacterCreationAdvisor runtime wiring smoke.")
    parser.add_argument(
        "--raw-root",
        default="",
        help="Optional existing data/compendium/fiveetools/raw root. If omitted, the smoke uses a fixture.",
    )
    parser.add_argument("--json-out", default="")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    smoke = CharacterCreationRuntimeWiringSmoke(project_root=PROJECT_ROOT)
    result = smoke.run_against_raw_root(args.raw_root) if args.raw_root else smoke.run()

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        if not args.quiet:
            print(f"CharacterCreation runtime wiring smoke JSON written: {out}")

    if args.quiet:
        print("OK" if result.ok else "FAIL")
    else:
        print(result.summary_text())

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
