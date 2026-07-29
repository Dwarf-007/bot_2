"""
SERVICES/GENERATORS/CAMPAIGN_ENRICHER.PY

Sprint 3: deterministic + optional LLM enrichment for procedural campaign bundles.

Input:
    room_data.json, room_lookup.json, rag_index.json, toc_index.json

Output:
    enrichment.json
    enriched room_data.json
    enriched rag_index.json

Design rules:
- Deterministic fallback is always available.
- LLM output is optional and schema-validated lightly.
- Existing generated facts are preserved; enrichment is appended under raw/enrichment
  and as additional RAG chunks.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.campaign_enrichment import (
    CampaignEnrichment,
    EnrichedFaction,
    EnrichedQuest,
    EnrichedRoom,
)
from services.generators.enrichment_prompt_builder import EnrichmentPromptBuilder
from services.generators.llm_json_utils import extract_json_object


class CampaignEnricher:
    def __init__(self, llm_adapter: Any = None, prompt_builder: Optional[EnrichmentPromptBuilder] = None) -> None:
        self.llm_adapter = llm_adapter
        self.prompt_builder = prompt_builder or EnrichmentPromptBuilder()

    def enrich_bundle(
        self,
        room_data: Dict[str, Any],
        room_lookup: Optional[Dict[str, Any]] = None,
        rag_index: Optional[Dict[str, Any]] = None,
        toc_index: Optional[Dict[str, Any]] = None,
        campaign_id: str = "default",
        campaign_name: Optional[str] = None,
        theme: str = "ancient cursed dungeon",
        tone: str = "grim exploration",
        use_llm: bool = False,
        max_rooms: Optional[int] = None,
    ) -> Dict[str, Any]:
        rooms = list((room_data or {}).get("rooms", []) or [])
        if max_rooms is not None:
            rooms_to_enrich = rooms[: max(0, int(max_rooms))]
        else:
            rooms_to_enrich = rooms
        campaign_name = campaign_name or campaign_id

        campaign_level = self._llm_campaign_enrichment(rooms_to_enrich, campaign_id, campaign_name, theme, tone) if use_llm and self.llm_adapter else None
        if campaign_level is None:
            campaign_level = self._deterministic_campaign_enrichment(rooms_to_enrich, campaign_id, campaign_name, theme, tone)

        enriched_rooms: list[EnrichedRoom] = []
        for room in rooms_to_enrich:
            enriched = self._llm_room_enrichment(room, theme, tone) if use_llm and self.llm_adapter else None
            if enriched is None:
                enriched = self._deterministic_room_enrichment(room, theme, tone)
            enriched_rooms.append(enriched)

        enrichment = CampaignEnrichment(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            theme=theme,
            premise=campaign_level.get("premise", self._default_premise(campaign_name, theme)),
            factions=[self._faction_from_dict(item) for item in campaign_level.get("factions", [])],
            quests=[self._quest_from_dict(item) for item in campaign_level.get("quests", [])],
            rooms=enriched_rooms,
            secrets=[str(item) for item in campaign_level.get("secrets", [])],
            rumors=[str(item) for item in campaign_level.get("rumors", [])],
            metadata={
                "source": "CampaignEnricher",
                "version": "sprint_3",
                "use_llm": bool(use_llm and self.llm_adapter),
                "room_count": len(rooms_to_enrich),
            },
        )

        enriched_room_data = self.merge_room_data(room_data, enrichment)
        enriched_rag_index = self.merge_rag_index(rag_index or {"campaign_id": campaign_id, "chunks": []}, enrichment)
        return {
            "enrichment": enrichment.to_dict(),
            "room_data": enriched_room_data,
            "room_lookup": room_lookup or {},
            "rag_index": enriched_rag_index,
            "toc_index": toc_index or {"campaign_id": campaign_id, "entries": []},
        }

    def write_enriched_bundle(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        campaign_id: str,
        campaign_name: Optional[str] = None,
        theme: str = "ancient cursed dungeon",
        tone: str = "grim exploration",
        use_llm: bool = False,
        max_rooms: Optional[int] = None,
    ) -> Dict[str, str]:
        src = Path(input_dir)
        dst = Path(output_dir)
        dst.mkdir(parents=True, exist_ok=True)
        room_data = self._read_json(src / "room_data.json", {"rooms": []})
        room_lookup = self._read_json(src / "room_lookup.json", {})
        rag_index = self._read_json(src / "rag_index.json", {"campaign_id": campaign_id, "chunks": []})
        toc_index = self._read_json(src / "toc_index.json", {"campaign_id": campaign_id, "entries": []})

        result = self.enrich_bundle(
            room_data=room_data,
            room_lookup=room_lookup,
            rag_index=rag_index,
            toc_index=toc_index,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            theme=theme,
            tone=tone,
            use_llm=use_llm,
            max_rooms=max_rooms,
        )

        outputs = {
            "enrichment": dst / "enrichment.json",
            "room_data": dst / "room_data.json",
            "room_lookup": dst / "room_lookup.json",
            "rag_index": dst / "rag_index.json",
            "toc_index": dst / "toc_index.json",
        }
        outputs["enrichment"].write_text(json.dumps(result["enrichment"], ensure_ascii=False, indent=2), encoding="utf-8")
        outputs["room_data"].write_text(json.dumps(result["room_data"], ensure_ascii=False, indent=2), encoding="utf-8")
        outputs["room_lookup"].write_text(json.dumps(result["room_lookup"], ensure_ascii=False, indent=2), encoding="utf-8")
        outputs["rag_index"].write_text(json.dumps(result["rag_index"], ensure_ascii=False, indent=2), encoding="utf-8")
        outputs["toc_index"].write_text(json.dumps(result["toc_index"], ensure_ascii=False, indent=2), encoding="utf-8")
        return {key: str(value) for key, value in outputs.items()}

    def merge_room_data(self, room_data: Dict[str, Any], enrichment: CampaignEnrichment) -> Dict[str, Any]:
        room_enrichment = {room.room_id: room for room in enrichment.rooms}
        output_rooms = []
        for room in list((room_data or {}).get("rooms", []) or []):
            item = dict(room)
            room_id = str(item.get("room_id"))
            enriched = room_enrichment.get(room_id)
            if enriched:
                raw = dict(item.get("raw", {}) or {})
                raw["enrichment"] = enriched.to_dict()
                item["raw"] = raw
                appended = [
                    "",
                    "Enrichment:",
                    enriched.boxed_text,
                    "GM notes: " + "; ".join(enriched.gm_notes) if enriched.gm_notes else "",
                    "Clues: " + "; ".join(enriched.clues) if enriched.clues else "",
                    "Complications: " + "; ".join(enriched.complications) if enriched.complications else "",
                ]
                item["facts"] = str(item.get("facts") or "") + "\n" + "\n".join(part for part in appended if part)
            output_rooms.append(item)
        return {"rooms": output_rooms}

    def merge_rag_index(self, rag_index: Dict[str, Any], enrichment: CampaignEnrichment) -> Dict[str, Any]:
        output = dict(rag_index or {})
        chunks = list(output.get("chunks", []) or [])
        campaign_chunk = {
            "campaign_id": enrichment.campaign_id,
            "chunk_id": f"{enrichment.campaign_id}_enrichment_overview",
            "room_id": None,
            "title": f"{enrichment.campaign_name} Enrichment Overview",
            "text": self._overview_text(enrichment),
            "tags": ["enrichment", "campaign_overview", "lore"],
            "npc_names": [],
            "monster_names": [],
            "trap_names": [],
            "keyword_hits": ["enrichment", "premise", "factions", "quests", "rumors"],
        }
        chunks.append(campaign_chunk)
        for room in enrichment.rooms:
            chunks.append(
                {
                    "campaign_id": enrichment.campaign_id,
                    "chunk_id": f"{enrichment.campaign_id}_room_{room.room_id}_enrichment",
                    "room_id": room.room_id,
                    "title": f"Room {room.room_id} Enrichment",
                    "text": "\n".join([room.boxed_text, *room.gm_notes, *room.clues, *room.complications]),
                    "tags": ["enrichment", "room", "boxed_text"],
                    "npc_names": [],
                    "monster_names": [],
                    "trap_names": [],
                    "keyword_hits": ["enrichment", "room", "clue", "complication"],
                }
            )
        output["campaign_id"] = output.get("campaign_id") or enrichment.campaign_id
        output["chunks"] = chunks
        return output

    def _llm_campaign_enrichment(self, rooms: List[Dict[str, Any]], campaign_id: str, campaign_name: str, theme: str, tone: str) -> Optional[Dict[str, Any]]:
        summary = {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "room_count": len(rooms),
            "sample_rooms": [
                {"room_id": r.get("room_id"), "title": r.get("title"), "exits": r.get("exits", {})}
                for r in rooms[:12]
            ],
        }
        prompt = self.prompt_builder.build_campaign_prompt(summary, theme, tone)
        try:
            parsed = extract_json_object(self.llm_adapter.generate(prompt))
        except Exception:
            return None
        if not parsed:
            return None
        return parsed

    def _llm_room_enrichment(self, room: Dict[str, Any], theme: str, tone: str) -> Optional[EnrichedRoom]:
        prompt = self.prompt_builder.build_room_prompt(room, theme, tone)
        try:
            parsed = extract_json_object(self.llm_adapter.generate(prompt))
        except Exception:
            return None
        if not parsed or not parsed.get("boxed_text"):
            return None
        return EnrichedRoom(
            room_id=str(room.get("room_id")),
            boxed_text=str(parsed.get("boxed_text")),
            gm_notes=[str(x) for x in parsed.get("gm_notes", []) if x],
            clues=[str(x) for x in parsed.get("clues", []) if x],
            complications=[str(x) for x in parsed.get("complications", []) if x],
            metadata={"source": "llm"},
        )

    def _deterministic_campaign_enrichment(self, rooms: List[Dict[str, Any]], campaign_id: str, campaign_name: str, theme: str, tone: str) -> Dict[str, Any]:
        room_ids = [str(r.get("room_id")) for r in rooms if r.get("room_id")]
        entrance = room_ids[0] if room_ids else None
        deepest = room_ids[-1] if room_ids else None
        return {
            "premise": self._default_premise(campaign_name, theme),
            "factions": [
                {
                    "faction_id": "dungeon_intruders",
                    "name": "Dungeon Intruders",
                    "agenda": "Scavenge what remains and avoid the deeper curse.",
                    "attitude": "neutral",
                    "rooms": room_ids[: max(1, min(5, len(room_ids)))],
                },
                {
                    "faction_id": "old_curse",
                    "name": "The Old Curse",
                    "agenda": "Keep the dungeon sealed through traps, omens and restless guardians.",
                    "attitude": "hostile",
                    "rooms": room_ids[-max(1, min(5, len(room_ids))):],
                },
            ],
            "quests": [
                {
                    "quest_id": "map_the_depths",
                    "title": "Map the Depths",
                    "hook": "The first chambers suggest the dungeon is larger and older than expected.",
                    "objective": "Explore the connected rooms and identify a safe route back to the entrance.",
                    "reward_hint": "Reliable routes, bypassed traps and recovered valuables.",
                    "related_rooms": [rid for rid in [entrance, deepest] if rid],
                }
            ],
            "secrets": [
                "Several architectural details imply the dungeon was repurposed after its original construction.",
                "Some traps appear newer than the masonry around them.",
            ],
            "rumors": [
                f"Locals whisper that {campaign_name} changes those who stay too long.",
                "Old maps disagree about where the lower passages should be.",
            ],
        }

    def _deterministic_room_enrichment(self, room: Dict[str, Any], theme: str, tone: str) -> EnrichedRoom:
        room_id = str(room.get("room_id"))
        title = str(room.get("title") or f"Room #{room_id}")
        exits = room.get("exits", {}) or {}
        traps = room.get("traps", []) or []
        exit_phrase = "No obvious exit breaks the walls." if not exits else "Passages lead " + ", ".join(sorted(exits.keys())) + "."
        trap_phrase = "A tense stillness suggests caution." if traps else "The chamber is quiet, but not necessarily safe."
        boxed = f"{title} lies under the weight of {theme}. {exit_phrase} {trap_phrase} Dust, old stone and faint echoes make every step feel deliberate."
        gm_notes = [
            "Use the existing exits exactly as listed in room_data.json.",
            "Do not reveal hidden or secret details until players investigate.",
        ]
        clues = [
            "Marks on the floor hint at previous movement through this area.",
        ]
        complications = []
        if traps:
            complications.append("A detected trap can become a tactical obstacle instead of immediate damage.")
        if len(exits) >= 3:
            complications.append("Multiple exits make this a good place for pursuit, ambush or getting separated.")
        return EnrichedRoom(
            room_id=room_id,
            boxed_text=boxed,
            gm_notes=gm_notes,
            clues=clues,
            complications=complications,
            metadata={"source": "deterministic", "theme": theme, "tone": tone},
        )

    def _overview_text(self, enrichment: CampaignEnrichment) -> str:
        factions = "\n".join(f"- {f.name}: {f.agenda}" for f in enrichment.factions)
        quests = "\n".join(f"- {q.title}: {q.objective}" for q in enrichment.quests)
        rumors = "\n".join(f"- {r}" for r in enrichment.rumors)
        secrets = "\n".join(f"- {s}" for s in enrichment.secrets)
        return f"Premise: {enrichment.premise}\n\nFactions:\n{factions}\n\nQuests:\n{quests}\n\nRumors:\n{rumors}\n\nSecrets:\n{secrets}"

    def _faction_from_dict(self, item: Dict[str, Any]) -> EnrichedFaction:
        return EnrichedFaction(
            faction_id=self._slug(item.get("faction_id") or item.get("name") or "faction"),
            name=str(item.get("name") or "Unnamed Faction"),
            agenda=str(item.get("agenda") or "No agenda defined."),
            attitude=str(item.get("attitude") or "unknown"),
            rooms=[str(x) for x in item.get("rooms", []) if x is not None],
            metadata={k: v for k, v in item.items() if k not in {"faction_id", "name", "agenda", "attitude", "rooms"}},
        )

    def _quest_from_dict(self, item: Dict[str, Any]) -> EnrichedQuest:
        return EnrichedQuest(
            quest_id=self._slug(item.get("quest_id") or item.get("title") or "quest"),
            title=str(item.get("title") or "Unnamed Quest"),
            hook=str(item.get("hook") or "The dungeon offers an unresolved mystery."),
            objective=str(item.get("objective") or "Explore and survive."),
            reward_hint=str(item.get("reward_hint") or "Treasure, information or safer passage."),
            related_rooms=[str(x) for x in item.get("related_rooms", []) if x is not None],
            metadata={k: v for k, v in item.items() if k not in {"quest_id", "title", "hook", "objective", "reward_hint", "related_rooms"}},
        )

    @staticmethod
    def _default_premise(campaign_name: str, theme: str) -> str:
        return f"{campaign_name} is a procedurally mapped dungeon shaped by {theme}; exploration reveals how its rooms, traps and factions connect."

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _slug(value: Any) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"[^0-9a-zA-ZáéíóöőúüűÁÉÍÓÖŐÚÜŰ]+", "_", text)
        return re.sub(r"_+", "_", text).strip("_")[:80] or "item"
