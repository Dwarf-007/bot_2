"""
MODES/SANDBOX/MODELS/SANDBOX_KNOWLEDGE_FOG.PY

Sprint 14.4 - Sandbox Mode "knowledge fog" model.

Unlike Dungeon Mode's cell-level Fog-of-War (see
models/corridor_visibility_models.py and
docs/architecture/fog_of_war_model.md), Sandbox Mode has no fixed grid to
reveal. Instead, "fog" here means which discrete world facts (locations,
NPCs, factions, and free-form facts) the party is currently allowed to know
about, matching the "knowledge fog" concept described in
docs/architecture/runtime_modes.md and fog_of_war_model.md.

This model is intentionally channel-scoped (with an optional player_id),
mirroring the scope convention already used elsewhere in the project (see
models/secret_discovery_models.py's SecretDiscoveryState.scope_id, and
Sprint 10's channel+campaign initial state-scope decision).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


@dataclass
class SandboxKnowledgeFog:
    """
    Tracks what a party (or an individual player) currently knows about a
    Sandbox world.

    Attributes:
        channel_id: Discord channel (or equivalent scope) this knowledge
            state belongs to.
        player_id: Optional player identifier for per-player knowledge
            tracking. Empty string means "shared party knowledge" for the
            channel, matching the deferred per-player scope noted in
            docs/architecture/runtime_modes.md ("Initial state scope:
            channel + campaign; deferred: channel + campaign + player").
        discovered_location_ids: Set of SandboxLocation.location_id values
            the party has discovered.
        known_npc_ids: Set of SandboxNPC.npc_id values the party has met or
            otherwise learned about.
        known_faction_ids: Set of SandboxFaction.faction_id values the party
            has learned about.
        revealed_facts: Ordered list of free-form fact strings revealed to
            the party (e.g. lore snippets, rumors confirmed true), kept in
            discovery order.
    """

    channel_id: str
    player_id: str = ""
    discovered_location_ids: Set[str] = field(default_factory=set)
    known_npc_ids: Set[str] = field(default_factory=set)
    known_faction_ids: Set[str] = field(default_factory=set)
    revealed_facts: List[str] = field(default_factory=list)

    def discover_location(self, location_id: str) -> bool:
        """
        Marks a location as discovered by this scope.

        Returns:
            True if this call newly discovered the location, False if it was
            already known (idempotent, mirrors RoomDiscoveryState.discover()
            semantics from models/room_discovery_models.py).
        """
        normalized = str(location_id or "").strip()
        if not normalized:
            return False
        if normalized in self.discovered_location_ids:
            return False
        self.discovered_location_ids.add(normalized)
        return True

    def learn_npc(self, npc_id: str) -> bool:
        """
        Marks an NPC as known by this scope.

        Returns:
            True if this call newly registered the NPC, False if it was
            already known.
        """
        normalized = str(npc_id or "").strip()
        if not normalized:
            return False
        if normalized in self.known_npc_ids:
            return False
        self.known_npc_ids.add(normalized)
        return True

    def learn_faction(self, faction_id: str) -> bool:
        """
        Marks a faction as known by this scope.

        Returns:
            True if this call newly registered the faction, False if it was
            already known.
        """
        normalized = str(faction_id or "").strip()
        if not normalized:
            return False
        if normalized in self.known_faction_ids:
            return False
        self.known_faction_ids.add(normalized)
        return True

    def reveal_fact(self, fact: str) -> bool:
        """
        Appends a free-form fact to the revealed facts log, if not already
        present.

        Returns:
            True if this call newly appended the fact, False if it was
            already present (exact string match).
        """
        normalized = str(fact or "").strip()
        if not normalized:
            return False
        if normalized in self.revealed_facts:
            return False
        self.revealed_facts.append(normalized)
        return True

    def knows_location(self, location_id: str) -> bool:
        return str(location_id or "").strip() in self.discovered_location_ids

    def knows_npc(self, npc_id: str) -> bool:
        return str(npc_id or "").strip() in self.known_npc_ids

    def knows_faction(self, faction_id: str) -> bool:
        return str(faction_id or "").strip() in self.known_faction_ids

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "player_id": self.player_id,
            "discovered_location_ids": sorted(self.discovered_location_ids),
            "known_npc_ids": sorted(self.known_npc_ids),
            "known_faction_ids": sorted(self.known_faction_ids),
            "revealed_facts": list(self.revealed_facts),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SandboxKnowledgeFog":
        data = data or {}
        return cls(
            channel_id=str(data.get("channel_id") or ""),
            player_id=str(data.get("player_id") or ""),
            discovered_location_ids={
                str(x) for x in (data.get("discovered_location_ids") or [])
            },
            known_npc_ids={
                str(x) for x in (data.get("known_npc_ids") or [])
            },
            known_faction_ids={
                str(x) for x in (data.get("known_faction_ids") or [])
            },
            revealed_facts=[str(x) for x in (data.get("revealed_facts") or [])],
        )
