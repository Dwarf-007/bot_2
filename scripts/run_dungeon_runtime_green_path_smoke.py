#!/usr/bin/env python3
"""Run the Sprint 12.4 Dungeon Runtime green-path smoke against a real bundle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.bootstrap import build_runtime
from services.dungeon_runtime_green_path_smoke_runner import DungeonRuntimeGreenPathSmokeRunner


def parse_args():
    parser = argparse.ArgumentParser(description="Run Dungeon Runtime green-path smoke commands.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--player-id", required=True)
    parser.add_argument("--reset-before", action="store_true")
    parser.add_argument("--bind-channel", action="store_true")
    parser.add_argument("--no-force-campaign", action="store_true")
    parser.add_argument("--json-out", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runtime = build_runtime()
    runner = DungeonRuntimeGreenPathSmokeRunner(
        game_turn_service=runtime.game_turn_service,
        campaign_repo=runtime.campaign_repo,
        project_root=".",
    )
    result = runner.run(
        campaign_id=args.campaign_id,
        channel_id=args.channel_id,
        player_id=args.player_id,
        reset_before=args.reset_before,
        bind_channel=args.bind_channel,
        force_campaign=not args.no_force_campaign,
    )
    print(result.summary_text())
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON written: {out}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
