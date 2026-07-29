"""
MODES/SANDBOX/MODELS/SANDBOX_WORLD_STATE.PY

Sprint 14.4 - Sandbox Mode core domain models.

These dataclasses represent the persistent, source-agnostic world state for
Sandbox Mode: a dynamically generated world that is not backed by a fixed
Donjon bundle or a fixed campaign PDF.

Design notes:
- SandboxLocation.linked_dungeon_id is a forward-looking field for Sprint 14.5
  (Hybrid Mode), allowing a Sandbox-generated location to be bound to a
  concrete Donjon-generated dungeon_id (see models/dungeon_graph_models.py /
  models/generated_dungeon.py for the Dungeon-side identifiers).
- SandboxNPC.relationships and SandboxFaction.dispositions are intentionally
  Dict[str, int] rather than Dict[str, str], to support numeric D&D-style
  disposition scales (e.g. -100..100, hostile..friendly) that can be
  compared, thresholded, and adjusted incrementally by game logic.
- All models are plain dataclasses with explicit to_dict()/from_dict()
  methods, following the same JSON-serialization contract used throughout
  the project (see models/corridor_visibility_models.py,
  models/campaign_progress.py) so they can be round-tripped through the
  repository layer without relying on dataclasses.asdict() edge cases
  (e.g. sets, nested dataclasses).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SandboxLocation:
    """
    A single node in the Sandbox world's location graph.

    Attributes:
        location_id: Stable identifier, unique within a campaign_id.
        campaign_id: Owning campaign/world identifier.
        parent_id: Optional parent location_id (e.g. a region containing a
            settlement, a settlement containing a building).
        title: Player-facing display name.
        facts: Free-form narrative/GM-facing description text.
        discovered: Whether the location has ever been revealed to any
            player (world-level discovery flag; per-player discovery is
            tracked separately in SandboxKnowledgeFog).
        connected_locations: List of location_id values reachable from this
            location (directed or undirected, interpreted by the movement/
            narration layer).
        linked_dungeon_id: Optional Donjon-generated dungeon_id this location
            is bound to. Populated in Sprint 14.5 when a Sandbox location is
            promoted into a structured Dungeon Mode bundle. None while the
            location has no structured dungeon behind it.
        metadata: Opaque, implementation-defined extra data (e.g. generation
            provenance, tags, danger rating).
    """

    location_id: str
    campaign_id: str
    parent_id: Optional[str] = None
    title: str = ""
    facts: str = ""
    discovered: bool = False
    connected_locations: List[str] = field(default_factory=list)
    linked_dungeon_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "location_id": self.location_id,
            "campaign_id": self.campaign_id,
            "parent_id": self.parent_id,
            "title": self.title,
            "facts": self.facts,
            "discovered": bool(self.discovered),
            "connected_locations": list(self.connected_locations),
            "linked_dungeon_id": self.linked_dungeon_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SandboxLocation":
        data = data or {}
        return cls(
            location_id=str(data.get("location_id") or ""),
            campaign_id=str(data.get("campaign_id") or ""),
            parent_id=cls._optional_str(data.get("parent_id")),
            title=str(data.get("title") or ""),
            facts=str(data.get("facts") or ""),
            discovered=bool(data.get("discovered", False)),
            connected_locations=[str(x) for x in (data.get("connected_locations") or [])],
            linked_dungeon_id=cls._optional_str(data.get("linked_dungeon_id")),
            metadata=dict(data.get("metadata") or {}),
        )

    @staticmethod
    def _optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


@dataclass
class SandboxNPC:
    """
    A single NPC identity tracked by the Sandbox world.

    Attributes:
        npc_id: Stable identifier, unique within a campaign_id.
        campaign_id: Owning campaign/world identifier.
        name: Player-facing display name.
        current_location_id: Optional location_id where the NPC currently is.
        relationships: Numeric disposition map keyed by another entity id
            (player_id, npc_id, or faction_id), e.g. {"player_123": 40,
            "npc_guard_captain": -10}. Positive values indicate favorable
            disposition, negative values indicate hostility, matching the
            same numeric convention used by SandboxFaction.dispositions.
        memory_logs: Ordered list of short textual memory entries the NPC
            has accumulated (most recent last), used to keep narration
            consistent across turns.
        metadata: Opaque, implementation-defined extra data (e.g. stat
            block reference, generation provenance, tags).
    """

    npc_id: str
    campaign_id: str
    name: str = ""
    current_location_id: Optional[str] = None
    relationships: Dict[str, int] = field(default_factory=dict)
    memory_logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "npc_id": self.npc_id,
            "campaign_id": self.campaign_id,
            "name": self.name,
            "current_location_id": self.current_location_id,
            "relationships": {str(k): int(v) for k, v in self.relationships.items()},
            "memory_logs": list(self.memory_logs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SandboxNPC":
        data = data or {}
        return cls(
            npc_id=str(data.get("npc_id") or ""),
            campaign_id=str(data.get("campaign_id") or ""),
            name=str(data.get("name") or ""),
            current_location_id=cls._optional_str(data.get("current_location_id")),
            relationships=cls._int_dict(data.get("relationships") or {}),
            memory_logs=[str(x) for x in (data.get("memory_logs") or [])],
            metadata=dict(data.get("metadata") or {}),
        )

    @staticmethod
    def _optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _int_dict(value: Dict[str, Any]) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for key, raw in (value or {}).items():
            try:
                result[str(key)] = int(raw)
            except (TypeError, ValueError):
                continue
        return result


@dataclass
class SandboxFaction:
    """
    A faction/organization tracked by the Sandbox world.

    Attributes:
        faction_id: Stable identifier, unique within a campaign_id.
        campaign_id: Owning campaign/world identifier.
        name: Player-facing display name.
        goals: Ordered list of short textual goal descriptions driving the
            faction's behavior over time.
        dispositions: Numeric disposition map keyed by another entity id
            (player_id, npc_id, or faction_id), using the same numeric
            convention as SandboxNPC.relationships (positive = favorable,
            negative = hostile).
        metadata: Opaque, implementation-defined extra data.
    """

    faction_id: str
    campaign_id: str
    name: str = ""
    goals: List[str] = field(default_factory=list)
    dispositions: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "faction_id": self.faction_id,
            "campaign_id": self.campaign_id,
            "name": self.name,
            "goals": list(self.goals),
            "dispositions": {str(k): int(v) for k, v in self.dispositions.items()},
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SandboxFaction":
        data = data or {}
        return cls(
            faction_id=str(data.get("faction_id") or ""),
            campaign_id=str(data.get("campaign_id") or ""),
            name=str(data.get("name") or ""),
            goals=[str(x) for x in (data.get("goals") or [])],
            dispositions=cls._int_dict(data.get("dispositions") or {}),
            metadata=dict(data.get("metadata") or {}),
        )

    @staticmethod
    def _int_dict(value: Dict[str, Any]) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for key, raw in (value or {}).items():
            try:
                result[str(key)] = int(raw)
            except (TypeError, ValueError):
                continue
        return result


@dataclass
class SandboxWorldState:
    """
    Root aggregate for a Sandbox-mode world.

    This is the top-level object handed to/from the repository layer. It
    embeds the full set of known locations/NPCs/factions for a campaign as
    dictionaries keyed by their respective ids, so callers can navigate the
    world graph in memory without repeated repository round-trips within a
    single turn.

    Attributes:
        campaign_id: Owning campaign/world identifier (primary key).
        current_region: Optional label of the broad region currently active
            for the party (e.g. a top-level SandboxLocation.location_id or a
            free-form region name).
        game_time: Free-form in-world clock/calendar representation
            (e.g. "Day 14, Evening"). Intentionally untyped to avoid forcing
            a specific calendar system at this layer.
        global_flags: Opaque world-level flag/state bag (quest flags,
            world-changing event markers, etc.).
        locations: All known SandboxLocation objects, keyed by location_id.
        npcs: All known SandboxNPC objects, keyed by npc_id.
        factions: All known SandboxFaction objects, keyed by faction_id.
    """

    campaign_id: str
    current_region: Optional[str] = None
    game_time: str = ""
    global_flags: Dict[str, Any] = field(default_factory=dict)
    locations: Dict[str, SandboxLocation] = field(default_factory=dict)
    npcs: Dict[str, SandboxNPC] = field(default_factory=dict)
    factions: Dict[str, SandboxFaction] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "current_region": self.current_region,
            "game_time": self.game_time,
            "global_flags": dict(self.global_flags),
            "locations": {
                location_id: location.to_dict()
                for location_id, location in self.locations.items()
            },
            "npcs": {
                npc_id: npc.to_dict()
                for npc_id, npc in self.npcs.items()
            },
            "factions": {
                faction_id: faction.to_dict()
                for faction_id, faction in self.factions.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SandboxWorldState":
        data = data or {}
        raw_locations = data.get("locations") or {}
        raw_npcs = data.get("npcs") or {}
        raw_factions = data.get("factions") or {}

        locations: Dict[str, SandboxLocation] = {}
        for location_id, raw_location in raw_locations.items():
            location = SandboxLocation.from_dict(raw_location)
            locations[str(location_id)] = location

        npcs: Dict[str, SandboxNPC] = {}
        for npc_id, raw_npc in raw_npcs.items():
            npc = SandboxNPC.from_dict(raw_npc)
            npcs[str(npc_id)] = npc

        factions: Dict[str, SandboxFaction] = {}
        for faction_id, raw_faction in raw_factions.items():
            faction = SandboxFaction.from_dict(raw_faction)
            factions[str(faction_id)] = faction

        return cls(
            campaign_id=str(data.get("campaign_id") or ""),
            current_region=cls._optional_str(data.get("current_region")),
            game_time=str(data.get("game_time") or ""),
            global_flags=dict(data.get("global_flags") or {}),
            locations=locations,
            npcs=npcs,
            factions=factions,
        )

    @staticmethod
    def _optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
