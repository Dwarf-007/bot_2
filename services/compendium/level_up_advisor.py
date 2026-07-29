"""
SERVICES/COMPENDIUM/LEVEL_UP_ADVISOR.PY
Advisory level-up checklist builder.

F1.8 purpose:
- Build a concise, DM/player-facing checklist for a class level-up.
- Use CharacterOptionService for class feature discovery.
- Optionally note spell review when SpellReferenceService is available or when
  the raw class entry suggests spellcasting.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No character sheet mutation.
- Not an authoritative character builder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from services.compendium.character_option_service import CharacterOptionService, ClassLevelFeature
from services.compendium.spell_reference_service import SpellReferenceService


@dataclass(frozen=True)
class LevelUpChecklistItem:
    label: str
    detail: str = ""
    source: str = ""


@dataclass(frozen=True)
class LevelUpAdvice:
    character_name: str
    class_name: str
    from_level: int
    to_level: int
    subclass_name: str = ""
    found_features: List[ClassLevelFeature] = field(default_factory=list)
    checklist: List[LevelUpChecklistItem] = field(default_factory=list)
    advisory_text: str = ""


class LevelUpAdvisor:
    """Builds advisory level-up summaries from compendium-backed character options."""

    def __init__(
        self,
        character_options: CharacterOptionService,
        spell_reference: Optional[SpellReferenceService] = None,
    ) -> None:
        self.character_options = character_options
        self.spell_reference = spell_reference

    def build_level_up_advice(
        self,
        character_name: str,
        class_name: str,
        from_level: int,
        to_level: int,
        subclass_name: str = "",
    ) -> LevelUpAdvice:
        safe_from = int(from_level)
        safe_to = int(to_level)
        features: List[ClassLevelFeature] = []
        checklist: List[LevelUpChecklistItem] = []

        if safe_to <= safe_from:
            checklist.append(LevelUpChecklistItem(
                label="Ellenőrizd a szinteket",
                detail="A cél szint nem magasabb a kiinduló szintnél.",
            ))
        else:
            for level in range(safe_from + 1, safe_to + 1):
                result = self.character_options.get_class_level_features(class_name, level, subclass_name=subclass_name)
                features.extend(result.features)
                if result.features:
                    for feature in result.features:
                        checklist.append(LevelUpChecklistItem(
                            label=f"Level {level}: {feature.name}",
                            detail=feature.snippet,
                            source=feature.source,
                        ))
                else:
                    checklist.append(LevelUpChecklistItem(
                        label=f"Level {level}: class feature review",
                        detail="Nem találtam explicit class feature-t az indexben; ellenőrizd a class progressiont a forrásban.",
                    ))

        checklist.extend(self._generic_level_up_items())
        if self.spell_reference is not None:
            checklist.append(LevelUpChecklistItem(
                label="Spellcasting review",
                detail="Ha a karakter spellcaster vagy spellcasting feature-t kap, ellenőrizd a spell listát, prepared/known spell szabályokat és spell slot progressiont.",
            ))

        advice = LevelUpAdvice(
            character_name=str(character_name or "Character"),
            class_name=str(class_name or "Class"),
            from_level=safe_from,
            to_level=safe_to,
            subclass_name=str(subclass_name or ""),
            found_features=features,
            checklist=checklist,
            advisory_text="",
        )
        return LevelUpAdvice(
            character_name=advice.character_name,
            class_name=advice.class_name,
            from_level=advice.from_level,
            to_level=advice.to_level,
            subclass_name=advice.subclass_name,
            found_features=advice.found_features,
            checklist=advice.checklist,
            advisory_text=self._build_advisory_text(advice),
        )

    @staticmethod
    def _generic_level_up_items() -> List[LevelUpChecklistItem]:
        return [
            LevelUpChecklistItem("HP update", "Dobd vagy számold az új HP-t a table policy szerint."),
            LevelUpChecklistItem("Proficiency bonus check", "Ellenőrizd, változik-e a proficiency bonus ezen a szinten."),
            LevelUpChecklistItem("Class resources", "Frissítsd a class resource-okat, használatszámokat és save DC-ket, ha releváns."),
            LevelUpChecklistItem("Character sheet update", "A végleges karakterlapot Avrae-ban/D&D Beyondban vagy a használt sheetben frissítsétek."),
        ]

    @staticmethod
    def _build_advisory_text(advice: LevelUpAdvice) -> str:
        title = f"Level-up advisory: {advice.character_name} — {advice.class_name} {advice.from_level} → {advice.to_level}"
        if advice.subclass_name:
            title += f" ({advice.subclass_name})"
        lines = [title, "", "Teendők:"]
        for item in advice.checklist:
            suffix = f" [{item.source}]" if item.source else ""
            detail = f" — {item.detail}" if item.detail else ""
            lines.append(f"- {item.label}{suffix}{detail}")
        lines.append("")
        lines.append("Ez advisory lista; a végső döntés és karakterlap-frissítés a DM/player feladata.")
        return "\n".join(lines)
