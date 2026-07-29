# services/campaign_manager.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.dungeons.dungeon_session import DungeonSession
from services.movement.movement_state_store import MovementStateStore
from services.visibility.visibility_state_store import VisibilityStateStore


class CampaignManager:
    """Handles campaign listing, selection, and session lifecycle."""

    def __init__(self, channel_repo, campaign_repo, combat_service=None, campaign_data_dir: str = "campaigns") -> None:
        self.channel_repo = channel_repo
        self.campaign_repo = campaign_repo
        self.campaigns_dir = Path(campaign_data_dir)
        self._sessions: Dict[str, DungeonSession] = {}
        self.combat_service = combat_service

    # ------------------------------------------------------------------
    # Campaign listing
    # ------------------------------------------------------------------
    def list_available_campaigns(self) -> List[Dict[str, Any]]:
        campaigns = []
        if not self.campaigns_dir.exists():
            return campaigns

        # 1. Hagyományos campaign_manifest.json fájlok
        for manifest_path in self.campaigns_dir.rglob("campaign_manifest.json"):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                campaigns.append({
                    "campaign_id": data.get("campaign_id") or manifest_path.parent.name,
                    "name": data.get("name") or data.get("campaign_name") or manifest_path.parent.name,
                    "type": data.get("type", "unknown"),
                    "recommended_starting_level": data.get("recommended_starting_level"),
                    "recommended_party_size": data.get("recommended_party_size"),
                    "description": data.get("description", ""),
                    "bundle_dir": str(manifest_path.parent),
                })
            except Exception:
                continue

        # 2. Donjon megadungeon manifestek
        for manifest_path in self.campaigns_dir.rglob("donjon_megadungeon_manifest.json"):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                bundle_dir = data.get("bundle_dir", str(manifest_path.parent.parent))
                campaigns.append({
                    "campaign_id": data.get("campaign_id") or manifest_path.parent.name,
                    "name": data.get("campaign_name") or data.get("campaign_id"),
                    "type": "generated",
                    "recommended_starting_level": data.get("plan", {}).get("level_start", 1),
                    "recommended_party_size": data.get("plan", {}).get("settings", {}).get("party_size"),
                    "description": f"Donjon megadungeon: {data.get('plan', {}).get('settings', {}).get('dungeon_size', '?')} méret, {len(data.get('levels', []))} szint.",
                    "bundle_dir": bundle_dir,
                    "manifest_path": str(manifest_path),
                })
            except Exception:
                continue

        return campaigns

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def select_campaign(
        self,
        channel_id: str,
        campaign_id: str,
        leveling_mode: str = "xp",
    ) -> Dict[str, Any]:
        state = self.channel_repo.get_state(channel_id)
        current_campaign = state.get("campaign_id", "default")
        if current_campaign != "default" and current_campaign != campaign_id:
            return {"ok": False, "message": "A csatornán már aktív kampány van. Előbb zárd le: `!campaign end`"}

        campaigns = self.list_available_campaigns()
        match = next((c for c in campaigns if c["campaign_id"] == campaign_id), None)
        bundle_dir = match.get("bundle_dir") if match else self._find_bundle_dir(campaign_id)
        if not bundle_dir:
            return {"ok": False, "message": f"Nem található a(z) '{campaign_id}' kampány bundle."}

        self.channel_repo.update_field(channel_id, "campaign_id", campaign_id)
        self.channel_repo.update_field(channel_id, "leveling_mode", leveling_mode)
        self.channel_repo.update_field(channel_id, "bundle_dir", str(bundle_dir))
        self.channel_repo.update_field(channel_id, "mode", "dungeon")

        return {
            "ok": True,
            "message": f"Kampány kiválasztva: `{campaign_id}`. A játékosok csatlakozhatnak `!join <név>` paranccsal. Indítás: `!campaign start`",
            "campaign_id": campaign_id,
        }

    def start_campaign(self, channel_id: str) -> Dict[str, Any]:
        state = self.channel_repo.get_state(channel_id)
        campaign_id = state.get("campaign_id", "default")
        if campaign_id == "default":
            return {"ok": False, "message": "Nincs kiválasztott kampány. Használd: `!campaign select <id>`"}

        bundle_dir = state.get("bundle_dir")
        if not bundle_dir:
            bundle_dir = self._find_bundle_dir(campaign_id)
        if not bundle_dir:
            return {"ok": False, "message": f"Nem található a(z) '{campaign_id}' kampány bundle."}

        session = DungeonSession(
            Path(bundle_dir), campaign_id,
            channel_id=channel_id,
            combat_service=self.combat_service,
        )

        graph_path = Path(bundle_dir) / "node_graph.json"
        if graph_path.exists():
            graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
            entrance_id = graph_data.get("entrance_node_id")
        else:
            # Fallback a régi dungeon_graph.json-ra (ha még nincs node_graph)
            graph_path_old = Path(bundle_dir) / "dungeon_graph.json"
            if graph_path_old.exists():
                old = json.loads(graph_path_old.read_text(encoding="utf-8"))
                entrance = old.get("entrance", {})
                entrance_id = entrance.get("room_id") or self._first_room(bundle_dir)
            else:
                entrance_id = self._first_room(bundle_dir)

        result = session.init_new_game(start_node_id=entrance_id)

        self._sessions[channel_id] = session

        return {
            "ok": True,
            "message": result.get("description", "A kaland kezdetét veszi."),
            "node": result.get("node"),
            "exits": result.get("exits"),
        }

    def end_campaign(self, channel_id: str) -> Dict[str, Any]:
        if channel_id in self._sessions:
            del self._sessions[channel_id]
        self.channel_repo.reset_state(channel_id)
        return {"ok": True, "message": "A kampány lezárva. A csatorna visszaállt az alapállapotba."}

    def get_session(self, channel_id: str) -> Optional[DungeonSession]:
        return self._sessions.get(channel_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _find_bundle_dir(self, campaign_id: str) -> Optional[Path]:
        for path in self.campaigns_dir.rglob("campaign_manifest.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("campaign_id") == campaign_id:
                    return path.parent
            except Exception:
                continue
        for path in self.campaigns_dir.rglob("donjon_megadungeon_manifest.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("campaign_id") == campaign_id:
                    return Path(data.get("bundle_dir", str(path.parent.parent)))
            except Exception:
                continue
        for name in [campaign_id, f"{campaign_id}_bundle_v3"]:
            candidate = self.campaigns_dir / name
            if candidate.exists():
                return candidate
        return None

    def _first_room(self, bundle_dir: str | Path) -> str:
        path = Path(bundle_dir) / "room_data.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            rooms = data.get("rooms", [])
            if rooms:
                return rooms[0].get("room_id", "unknown")
        return "unknown"