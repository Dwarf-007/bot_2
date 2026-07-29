"""
SERVICES/GENERATORS/CAMPAIGN_BUNDLE_BUILDER.PY

Sprint 2: Convert a source-agnostic GeneratedDungeon into the existing campaign
bundle files consumed by tools/import_campaign_bundle.py:

- room_data.json
- room_lookup.json
- rag_index.json
- toc_index.json

This module is intentionally deterministic and does not call an LLM.
AI enrichment belongs to Sprint 3.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class CampaignBundleBuilder:
    """Build existing campaign-bundle JSON files from GeneratedDungeon data."""

    def build_bundle(
        self,
        generated_dungeon: Any,
        campaign_id: str,
        campaign_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        dungeon = self._to_dict(generated_dungeon)
        campaign_id = str(campaign_id or dungeon.get("dungeon_id") or "generated_campaign").strip()
        if not campaign_id:
            raise ValueError("campaign_id is required")
        campaign_name = campaign_name or dungeon.get("title") or campaign_id

        rooms = self.build_room_data(dungeon, campaign_id)
        lookup = self.build_room_lookup(rooms)
        rag = self.build_rag_index(dungeon, campaign_id, rooms)
        toc = self.build_toc_index(dungeon, campaign_id, rooms)

        manifest = {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "source": dungeon.get("source", "generated_dungeon"),
            "dungeon_id": dungeon.get("dungeon_id"),
            "dungeon_title": dungeon.get("title"),
            "room_count": len(rooms),
            "rag_chunk_count": len(rag.get("chunks", [])),
            "lookup_count": len(lookup),
            "toc_entry_count": len(toc.get("entries", [])),
            "builder": "CampaignBundleBuilder",
            "builder_version": "sprint_2",
        }
        return {
            "manifest": manifest,
            "room_data": {"rooms": rooms},
            "room_lookup": lookup,
            "rag_index": rag,
            "toc_index": toc,
        }

    def write_bundle(
        self,
        generated_dungeon: Any,
        campaign_id: str,
        output_dir: str | Path,
        campaign_name: Optional[str] = None,
    ) -> Dict[str, str]:
        bundle = self.build_bundle(generated_dungeon, campaign_id=campaign_id, campaign_name=campaign_name)
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)

        outputs = {
            "room_data": root / "room_data.json",
            "room_lookup": root / "room_lookup.json",
            "rag_index": root / "rag_index.json",
            "toc_index": root / "toc_index.json",
            "manifest": root / "campaign_bundle_manifest.json",
        }
        outputs["room_data"].write_text(json.dumps(bundle["room_data"], ensure_ascii=False, indent=2), encoding="utf-8")
        outputs["room_lookup"].write_text(json.dumps(bundle["room_lookup"], ensure_ascii=False, indent=2), encoding="utf-8")
        outputs["rag_index"].write_text(json.dumps(bundle["rag_index"], ensure_ascii=False, indent=2), encoding="utf-8")
        outputs["toc_index"].write_text(json.dumps(bundle["toc_index"], ensure_ascii=False, indent=2), encoding="utf-8")
        outputs["manifest"].write_text(json.dumps(bundle["manifest"], ensure_ascii=False, indent=2), encoding="utf-8")
        return {key: str(value) for key, value in outputs.items()}

    def build_room_data(self, dungeon: Dict[str, Any], campaign_id: str) -> List[Dict[str, Any]]:
        connections = [self._to_dict(item) for item in dungeon.get("connections", [])]
        doors = {str(door.get("door_id")): door for door in [self._to_dict(item) for item in dungeon.get("doors", [])]}
        traps = [self._to_dict(item) for item in dungeon.get("traps", [])]
        trap_points = {(int(t.get("x", -1)), int(t.get("y", -1))) for t in traps}

        rooms: list[dict[str, Any]] = []
        for order_index, room in enumerate([self._to_dict(item) for item in dungeon.get("rooms", [])], start=1):
            room_id = str(room.get("room_id") or order_index)
            title = str(room.get("title") or f"Room #{room_id}")
            exits = self._exits_for_room(room_id, connections)
            room_connections = self._connections_for_room(room_id, connections)
            room_doors = self._doors_for_connections(room_connections, doors)
            room_traps = self._traps_near_room(room, traps, trap_points)
            slug = self._slug(title or room_id)
            facts = self._room_facts(room, exits, room_connections, room_doors, room_traps)

            rooms.append(
                {
                    "campaign_id": campaign_id,
                    "room_id": room_id,
                    "title": title,
                    "room_slug": slug,
                    "facts": facts,
                    "exits": exits,
                    "monsters": room.get("monsters", []) or [],
                    "traps": room_traps,
                    "treasures": room.get("treasures", []) or [],
                    "features": room.get("features", []) or [],
                    "is_entrance": bool(room.get("is_entrance", False)),
                    "source_chunk_ids": [f"{campaign_id}_room_{room_id}"],
                    "raw": {
                        "source": dungeon.get("source", "generated_dungeon"),
                        "dungeon_id": dungeon.get("dungeon_id"),
                        "dungeon_title": dungeon.get("title"),
                        "order_index": order_index,
                        "is_entrance": bool(room.get("is_entrance", False)),
                        "geometry": {
                            "x": room.get("x"),
                            "y": room.get("y"),
                            "width": room.get("width"),
                            "height": room.get("height"),
                            "cell_count": len(room.get("cells", []) or []),
                        },
                        "connections": room_connections,
                        "doors": room_doors,
                        "metadata": room.get("metadata", {}) or {},
                    },
                }
            )
        return rooms

    def build_room_lookup(self, rooms: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        lookup: dict[str, dict[str, Any]] = {}
        for room in rooms:
            room_id = str(room["room_id"])
            title = str(room.get("title") or room_id)
            slug = str(room.get("room_slug") or self._slug(title))
            payload = {"room_id": room_id, "title": title, "slug": slug}
            for alias in self._aliases_for_room(room_id, title, slug):
                lookup[alias] = payload
        return dict(sorted(lookup.items(), key=lambda item: item[0].lower()))

    def build_rag_index(self, dungeon: Dict[str, Any], campaign_id: str, rooms: List[Dict[str, Any]]) -> Dict[str, Any]:
        chunks: list[dict[str, Any]] = []
        for room in rooms:
            room_id = str(room["room_id"])
            title = str(room.get("title") or room_id)
            facts = str(room.get("facts") or "")
            exits = room.get("exits", {}) or {}
            trap_names = [str(t.get("kind") or "trap") for t in room.get("traps", [])]
            keyword_hits = ["donjon", "generated", "dungeon", "room", *list(exits.keys()), *trap_names]
            chunks.append(
                {
                    "campaign_id": campaign_id,
                    "chunk_id": f"{campaign_id}_room_{room_id}",
                    "room_id": room_id,
                    "title": title,
                    "text": facts,
                    "tags": ["donjon", "generated_dungeon", "room"],
                    "npc_names": [],
                    "monster_names": [str(m.get("name")) for m in room.get("monsters", []) if isinstance(m, dict) and m.get("name")],
                    "trap_names": trap_names,
                    "keyword_hits": sorted(set(k for k in keyword_hits if k)),
                }
            )
        return {
            "campaign_id": campaign_id,
            "source": dungeon.get("source", "generated_dungeon"),
            "chunks": chunks,
        }

    def build_toc_index(self, dungeon: Dict[str, Any], campaign_id: str, rooms: List[Dict[str, Any]]) -> Dict[str, Any]:
        entries = []
        for index, room in enumerate(rooms, start=1):
            room_id = str(room["room_id"])
            title = str(room.get("title") or room_id)
            entries.append(
                {
                    "campaign_id": campaign_id,
                    "scene_id": self._slug(title) or f"room_{room_id}",
                    "title": title,
                    "order_index": index,
                    "room_id": room_id,
                    "source": "donjon_generated_room",
                    "metadata": {
                        "source_chunk_ids": room.get("source_chunk_ids", []),
                        "source": dungeon.get("source", "generated_dungeon"),
                    },
                }
            )
        return {"campaign_id": campaign_id, "entries": entries}

    def _room_facts(
        self,
        room: Dict[str, Any],
        exits: Dict[str, str],
        connections: List[Dict[str, Any]],
        doors: List[Dict[str, Any]],
        traps: List[Dict[str, Any]],
    ) -> str:
        title = str(room.get("title") or f"Room #{room.get('room_id')}")
        geometry = f"Grid position x={room.get('x')}, y={room.get('y')}; size {room.get('width')}x{room.get('height')} cells."
        exit_text = "No known exits." if not exits else "Exits: " + ", ".join(f"{direction} → room {target}" for direction, target in sorted(exits.items())) + "."
        connection_text = self._connection_facts(connections)
        door_text = self._door_facts(doors)
        trap_text = self._trap_facts(traps)
        feature_items = [str(item) for item in room.get("features", []) or []]
        feature_text = "Features: " + "; ".join(feature_items) + "." if feature_items else "Features: generated room geometry only; narrative enrichment pending."
        return "\n".join(part for part in [f"{title}.", geometry, exit_text, connection_text, door_text, trap_text, feature_text] if part)

    def _connection_facts(self, connections: List[Dict[str, Any]]) -> str:
        if not connections:
            return "Connections: none inferred."
        parts = []
        for connection in connections:
            other = connection.get("to_room_id") or connection.get("from_room_id")
            parts.append(
                f"{connection.get('via', 'corridor')} to room {other}"
                + ("; locked" if connection.get("locked") else "")
                + ("; trapped" if connection.get("trapped") else "")
                + ("; secret" if connection.get("secret") else "")
            )
        return "Connections: " + "; ".join(parts) + "."

    def _door_facts(self, doors: List[Dict[str, Any]]) -> str:
        if not doors:
            return "Doors: none attached to inferred connections."
        parts = []
        for door in doors[:12]:
            flags = [flag for flag in ["locked" if door.get("locked") else "", "trapped" if door.get("trapped") else "", "secret" if door.get("secret") else ""] if flag]
            parts.append(f"{door.get('kind', 'door')} at ({door.get('x')},{door.get('y')})" + (f" [{', '.join(flags)}]" if flags else ""))
        suffix = " ..." if len(doors) > 12 else ""
        return "Doors: " + "; ".join(parts) + suffix + "."

    def _trap_facts(self, traps: List[Dict[str, Any]]) -> str:
        if not traps:
            return "Traps: none detected in or near this room."
        return "Traps: " + "; ".join(f"{trap.get('kind', 'trap')} at ({trap.get('x')},{trap.get('y')})" for trap in traps[:12]) + (" ..." if len(traps) > 12 else "") + "."

    def _exits_for_room(self, room_id: str, connections: List[Dict[str, Any]]) -> Dict[str, str]:
        exits: dict[str, str] = {}
        fallback_counter = 1
        for connection in connections:
            from_room = str(connection.get("from_room_id"))
            to_room = str(connection.get("to_room_id"))
            direction = connection.get("direction")
            if from_room == room_id:
                key = str(direction or f"exit_{fallback_counter}")
                exits[key] = to_room
                fallback_counter += 1
            elif to_room == room_id:
                key = self._opposite(str(direction)) if direction else f"exit_{fallback_counter}"
                exits[key] = from_room
                fallback_counter += 1
        return dict(sorted(exits.items()))

    def _connections_for_room(self, room_id: str, connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for connection in connections:
            if str(connection.get("from_room_id")) == room_id:
                result.append(connection)
            elif str(connection.get("to_room_id")) == room_id:
                mirrored = dict(connection)
                mirrored["from_room_id"], mirrored["to_room_id"] = mirrored["to_room_id"], mirrored["from_room_id"]
                mirrored["direction"] = self._opposite(str(mirrored.get("direction"))) if mirrored.get("direction") else None
                result.append(mirrored)
        return result

    def _doors_for_connections(self, connections: List[Dict[str, Any]], doors: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen: set[str] = set()
        output: list[dict[str, Any]] = []
        for connection in connections:
            for door_id in connection.get("door_ids", []) or []:
                if door_id in seen:
                    continue
                door = doors.get(str(door_id))
                if door:
                    output.append(door)
                    seen.add(str(door_id))
        return output

    def _traps_near_room(self, room: Dict[str, Any], traps: List[Dict[str, Any]], trap_points: set[tuple[int, int]]) -> List[Dict[str, Any]]:
        cells = [(int(x), int(y)) for x, y in room.get("cells", []) or []]
        if not cells:
            return []
        min_x = min(x for x, _ in cells) - 1
        max_x = max(x for x, _ in cells) + 1
        min_y = min(y for _, y in cells) - 1
        max_y = max(y for _, y in cells) + 1
        output = []
        for trap in traps:
            x = int(trap.get("x", -9999))
            y = int(trap.get("y", -9999))
            if min_x <= x <= max_x and min_y <= y <= max_y:
                output.append(trap)
        return output

    def _aliases_for_room(self, room_id: str, title: str, slug: str) -> Iterable[str]:
        candidates = {
            str(room_id),
            f"room {room_id}",
            f"room #{room_id}",
            f"#{room_id}",
            str(title),
            str(slug),
        }
        return sorted(alias for alias in candidates if alias and alias.strip())

    @staticmethod
    def _opposite(direction: str) -> str:
        return {"north": "south", "south": "north", "east": "west", "west": "east"}.get(direction, direction)

    @staticmethod
    def _slug(value: str) -> str:
        text = str(value or "").strip().lower()
        replacements = {"û": "u", "ű": "u", "ú": "u", "ü": "u", "ő": "o", "ó": "o", "ö": "o", "á": "a", "é": "e", "í": "i"}
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = re.sub(r"[^0-9a-zA-Z]+", "_", text)
        return re.sub(r"_+", "_", text).strip("_")[:100]

    def _to_dict(self, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if is_dataclass(value):
            return asdict(value)
        if hasattr(value, "to_dict"):
            data = value.to_dict()
            if isinstance(data, dict):
                return data
        raise TypeError(f"Unsupported generated dungeon object: {type(value)!r}")
