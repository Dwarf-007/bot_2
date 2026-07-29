#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from app.bootstrap import build_runtime
from services.dungeon_runtime_mvp_smoke_runner import DungeonRuntimeMvpSmokeRunner

def parse_args():
    p=argparse.ArgumentParser(description="Run Dungeon Runtime MVP smoke commands against a real runtime bundle.")
    p.add_argument("--campaign-id", required=True)
    p.add_argument("--channel-id", required=True)
    p.add_argument("--player-id", required=True)
    p.add_argument("--reset-before", action="store_true")
    p.add_argument("--remove-debug-mirror-on-reset", action="store_true")
    p.add_argument("--no-force-campaign", action="store_true", help="Disable campaign_id_override when calling GameTurnService.process().")
    p.add_argument("--bind-channel", action="store_true", help="Also save channel state campaign_id/mode=dungeon before smoke.")
    p.add_argument("--json-out", default="")
    return p.parse_args()

def main() -> int:
    args=parse_args()
    rt=build_runtime()
    runner=DungeonRuntimeMvpSmokeRunner(game_turn_service=rt.game_turn_service, campaign_repo=rt.campaign_repo, project_root=".")
    result=runner.run(campaign_id=args.campaign_id, channel_id=args.channel_id, player_id=args.player_id, reset_before=args.reset_before, remove_debug_mirror_on_reset=args.remove_debug_mirror_on_reset, force_campaign=not args.no_force_campaign, bind_channel=args.bind_channel)
    print(result.summary_text())
    if args.json_out:
        out=Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON written: {out}")
    return 0 if result.ok else 1
if __name__ == "__main__":
    raise SystemExit(main())
