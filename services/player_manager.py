# services/player_manager.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class PlayerManager:
    """Játékos csatlakozási kérelmek és jóváhagyott játékosok kezelése."""

    def __init__(self, channel_repo) -> None:
        self.channel_repo = channel_repo

    # ------------------------------------------------------------------
    # Csatlakozási kérelem
    # ------------------------------------------------------------------
    def request_join(self, channel_id: str, user_id: str, character_name: str) -> Dict[str, Any]:
        """Játékos csatlakozási kérelmet ad a pending listához."""
        state = self.channel_repo.get_state(channel_id)

        # Ellenőrizzük, hogy a játékos már tag-e
        party = list(state.get("party", []))
        if any(p.get("user_id") == user_id for p in party):
            return {"ok": False, "message": "Már tagja vagy a csapatnak."}

        # Pending lista
        pending = list(state.get("pending_players", []))
        if any(p.get("user_id") == user_id for p in pending):
            return {"ok": False, "message": "Már van függő csatlakozási kérelmed."}

        pending.append(
            {
                "user_id": user_id,
                "character_name": character_name,
                "requested_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        state["pending_players"] = pending
        self.channel_repo.save_state(channel_id, state)

        return {"ok": True, "message": f"Csatlakozási kérelem elküldve: **{character_name}**. A DM hamarosan jóváhagyja."}

    # ------------------------------------------------------------------
    # Jóváhagyás / elutasítás
    # ------------------------------------------------------------------
    def approve(self, channel_id: str, user_id: str) -> Dict[str, Any]:
        """Jóváhagy egy függő csatlakozási kérelmet."""
        state = self.channel_repo.get_state(channel_id)
        pending = list(state.get("pending_players", []))
        party = list(state.get("party", []))

        target = None
        for i, p in enumerate(pending):
            if p["user_id"] == user_id:
                target = pending.pop(i)
                break
        if not target:
            return {"ok": False, "message": "Nincs ilyen függő kérelem."}

        target["approved_at"] = datetime.now(timezone.utc).isoformat()
        party.append(target)
        state["pending_players"] = pending
        state["party"] = party
        self.channel_repo.save_state(channel_id, state)

        return {"ok": True, "message": f"{target['character_name']} csatlakozott a csapathoz."}

    def deny(self, channel_id: str, user_id: str) -> Dict[str, Any]:
        """Elutasít egy függő csatlakozási kérelmet."""
        state = self.channel_repo.get_state(channel_id)
        pending = list(state.get("pending_players", []))

        target = None
        for i, p in enumerate(pending):
            if p["user_id"] == user_id:
                target = pending.pop(i)
                break
        if not target:
            return {"ok": False, "message": "Nincs ilyen függő kérelem."}

        state["pending_players"] = pending
        self.channel_repo.save_state(channel_id, state)

        return {"ok": True, "message": f"{target['character_name']} kérelme elutasítva."}

    # ------------------------------------------------------------------
    # Lekérdezések
    # ------------------------------------------------------------------
    def list_pending(self, channel_id: str) -> List[Dict[str, Any]]:
        """Visszaadja a függő kérelmek listáját."""
        state = self.channel_repo.get_state(channel_id)
        return list(state.get("pending_players", []))

    def list_party(self, channel_id: str) -> List[Dict[str, Any]]:
        """Visszaadja a jóváhagyott játékosok listáját."""
        state = self.channel_repo.get_state(channel_id)
        return list(state.get("party", []))

    def is_member(self, channel_id: str, user_id: str) -> bool:
        """Ellenőrzi, hogy a játékos tagja-e a csapatnak."""
        party = self.list_party(channel_id)
        return any(p.get("user_id") == user_id for p in party)