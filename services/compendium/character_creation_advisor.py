"""
SERVICES/COMPENDIUM/CHARACTER_CREATION_ADVISOR.PY
Advisory character creation helper built on the F1 compendium foundation.

F2.1 purpose:
- Build a player/DM-facing character creation checklist.
- Use CharacterOptionService for selected class/species/background/feat lookup.
- Optionally use RulesReferenceService and SpellReferenceService as advisory
  references.
- Support role-aware suggestions useful for sandbox and donjon/megadungeon play.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No D&D Beyond integration.
- No LLM calls.
- No database dependency.
- Does not mutate character sheets.
- Not an authoritative character builder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from services.compendium.character_option_service import CharacterOptionService, CharacterOptionResult
from services.compendium.rules_reference_service import RulesReferenceService
from services.compendium.spell_reference_service import SpellReferenceService


class CharacterBuildRole(str, Enum):
    FRONTLINER = "frontliner"
    HEALER = "healer"
    SCOUT = "scout"
    CONTROLLER = "controller"
    STRIKER = "striker"
    SUPPORT = "support"
    FACE = "face"
    UTILITY = "utility"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CharacterCreationRequest:
    """Input for advisory character creation."""

    concept: str = ""
    starting_level: int = 1
    selected_class: str = ""
    selected_species: str = ""
    selected_background: str = ""
    selected_feat: str = ""
    preferred_role: CharacterBuildRole | str = CharacterBuildRole.UNKNOWN
    ability_score_method: str = ""
    include_spell_review: bool = True
    include_donjon_readiness: bool = False
    include_sandbox_readiness: bool = False


@dataclass(frozen=True)
class CharacterCreationChecklistItem:
    label: str
    detail: str = ""
    category: str = "general"
    required: bool = False


@dataclass(frozen=True)
class CharacterCreationLookupSummary:
    label: str
    query: str
    found: bool
    top_match_name: str = ""
    source: str = ""
    snippet: str = ""


@dataclass(frozen=True)
class CharacterCreationAdvice:
    concept: str
    starting_level: int
    preferred_role: str
    selected_class: str = ""
    selected_species: str = ""
    selected_background: str = ""
    selected_feat: str = ""
    lookups: List[CharacterCreationLookupSummary] = field(default_factory=list)
    checklist: List[CharacterCreationChecklistItem] = field(default_factory=list)
    missing_choices: List[str] = field(default_factory=list)
    advisory_text: str = ""


class CharacterCreationAdvisor:
    """Builds advisory character creation checklists."""

    SPELLCASTER_CLASSES = {
        "artificer",
        "bard",
        "cleric",
        "druid",
        "paladin",
        "ranger",
        "sorcerer",
        "warlock",
        "wizard",
    }

    ROLE_SUGGESTIONS = {
        CharacterBuildRole.FRONTLINER.value: [
            "Prioritize survivability: AC, HP, Constitution, and reliable melee options.",
            "Common class directions: Fighter, Paladin, Barbarian, some Cleric builds.",
            "Useful proficiencies: Athletics, shield/armor access, melee weapon support.",
        ],
        CharacterBuildRole.HEALER.value: [
            "Review healing, restoration, and emergency recovery options.",
            "Common class directions: Cleric, Druid, Bard, Paladin, some Ranger builds.",
            "Prepare a plan for revives, condition removal, and resource conservation.",
        ],
        CharacterBuildRole.SCOUT.value: [
            "Prioritize Stealth, Perception, Investigation, and mobility.",
            "Common class directions: Rogue, Ranger, Monk, Bard.",
            "For donjon/megadungeon play, thieves' tools and trap awareness are especially valuable.",
        ],
        CharacterBuildRole.CONTROLLER.value: [
            "Look for battlefield control, debuffs, area denial, and forced movement.",
            "Common class directions: Wizard, Druid, Bard, Sorcerer.",
            "Coordinate with the party so control spells do not block allies unnecessarily.",
        ],
        CharacterBuildRole.STRIKER.value: [
            "Prioritize reliable damage, accuracy, and action economy.",
            "Common class directions: Rogue, Fighter, Ranger, Warlock, Sorcerer.",
            "Check how the build handles resistant enemies and limited resources.",
        ],
        CharacterBuildRole.SUPPORT.value: [
            "Prioritize buffs, protection, utility, and party resource efficiency.",
            "Common class directions: Bard, Cleric, Druid, Artificer, Wizard.",
            "Make sure your support options match the campaign's expected threats.",
        ],
        CharacterBuildRole.FACE.value: [
            "Prioritize Charisma, social skills, languages, and social background hooks.",
            "Common class directions: Bard, Warlock, Sorcerer, Paladin, Rogue.",
            "Useful skills: Persuasion, Deception, Insight, Intimidation.",
        ],
        CharacterBuildRole.UTILITY.value: [
            "Prioritize flexible problem solving: rituals, tools, languages, and exploration support.",
            "Common class directions: Wizard, Bard, Artificer, Druid, Rogue.",
            "Make sure the character has useful non-combat contributions.",
        ],
    }

    def __init__(
        self,
        character_options: CharacterOptionService,
        spell_reference: Optional[SpellReferenceService] = None,
        rules_reference: Optional[RulesReferenceService] = None,
    ) -> None:
        self.character_options = character_options
        self.spell_reference = spell_reference
        self.rules_reference = rules_reference

    def build_advice(self, request: CharacterCreationRequest) -> CharacterCreationAdvice:
        role = self._normalize_role(request.preferred_role)
        lookups: List[CharacterCreationLookupSummary] = []
        checklist: List[CharacterCreationChecklistItem] = []
        missing: List[str] = []

        if request.selected_class:
            lookups.append(self._lookup_summary("Class", request.selected_class, self.character_options.lookup_class(request.selected_class)))
        else:
            missing.append("class")
            checklist.append(CharacterCreationChecklistItem("Choose a class", "Válassz class-t a karakter koncepciójához.", "core", True))

        if request.selected_species:
            lookups.append(self._lookup_summary("Species", request.selected_species, self.character_options.lookup_species(request.selected_species)))
        else:
            missing.append("species")
            checklist.append(CharacterCreationChecklistItem("Choose a species", "Válassz species/race opciót.", "core", True))

        if request.selected_background:
            lookups.append(self._lookup_summary("Background", request.selected_background, self.character_options.lookup_background(request.selected_background)))
        else:
            missing.append("background")
            checklist.append(CharacterCreationChecklistItem("Choose a background", "Válassz backgroundot és ellenőrizd a proficienciákat.", "core", True))

        if request.selected_feat:
            lookups.append(self._lookup_summary("Feat", request.selected_feat, self.character_options.lookup_feat(request.selected_feat)))

        if not request.ability_score_method:
            missing.append("ability_score_method")
            checklist.append(CharacterCreationChecklistItem(
                "Choose ability score method",
                "Döntsétek el: standard array, point buy, rolled stats vagy campaign-specific módszer.",
                "core",
                True,
            ))

        checklist.extend(self._core_checklist(request))
        checklist.extend(self._role_checklist(role))

        if request.include_spell_review and self._class_may_need_spell_review(request.selected_class):
            checklist.append(CharacterCreationChecklistItem(
                "Spellcasting review",
                "Ellenőrizd a spellcasting feature-t, known/prepared spell szabályokat, cantripeket és spell slot progressiont.",
                "spells",
                False,
            ))

        if request.include_donjon_readiness:
            checklist.extend(self._donjon_readiness_checklist(role))
        if request.include_sandbox_readiness:
            checklist.extend(self._sandbox_readiness_checklist())

        advice = CharacterCreationAdvice(
            concept=str(request.concept or "").strip(),
            starting_level=max(1, int(request.starting_level or 1)),
            preferred_role=role,
            selected_class=str(request.selected_class or "").strip(),
            selected_species=str(request.selected_species or "").strip(),
            selected_background=str(request.selected_background or "").strip(),
            selected_feat=str(request.selected_feat or "").strip(),
            lookups=lookups,
            checklist=checklist,
            missing_choices=missing,
            advisory_text="",
        )
        return CharacterCreationAdvice(
            concept=advice.concept,
            starting_level=advice.starting_level,
            preferred_role=advice.preferred_role,
            selected_class=advice.selected_class,
            selected_species=advice.selected_species,
            selected_background=advice.selected_background,
            selected_feat=advice.selected_feat,
            lookups=advice.lookups,
            checklist=advice.checklist,
            missing_choices=advice.missing_choices,
            advisory_text=self._build_advisory_text(advice),
        )

    def _lookup_summary(self, label: str, query: str, result: CharacterOptionResult) -> CharacterCreationLookupSummary:
        if not result.found:
            return CharacterCreationLookupSummary(label=label, query=query, found=False)
        top = result.matches[0]
        return CharacterCreationLookupSummary(
            label=label,
            query=query,
            found=True,
            top_match_name=top.name,
            source=top.source,
            snippet=top.snippet,
        )

    @staticmethod
    def _normalize_role(role: CharacterBuildRole | str) -> str:
        if isinstance(role, CharacterBuildRole):
            return role.value
        value = str(role or "").strip().lower()
        return value if value in {item.value for item in CharacterBuildRole} else CharacterBuildRole.UNKNOWN.value

    def _core_checklist(self, request: CharacterCreationRequest) -> List[CharacterCreationChecklistItem]:
        level = max(1, int(request.starting_level or 1))
        items = [
            CharacterCreationChecklistItem("Review level 1 class features", "Ellenőrizd a class induló feature-jeit és proficienciáit.", "core", True),
            CharacterCreationChecklistItem("Choose skill proficiencies", "Válaszd ki a class/background/species által adott skill proficienciákat.", "core", True),
            CharacterCreationChecklistItem("Review starting equipment", "Ellenőrizd a starting equipmentet vagy gold-buy szabályt.", "equipment", True),
            CharacterCreationChecklistItem("Calculate HP and AC", "Számold ki a kezdő HP-t, AC-t és mentődobás/proficiency értékeket.", "stats", True),
            CharacterCreationChecklistItem("Record character sheet", "A végleges karakterlapot Avrae-ban, D&D Beyondban vagy a használt sheet toolban rögzítsétek.", "sheet", True),
        ]
        if level > 1:
            items.append(CharacterCreationChecklistItem(
                "Review higher-level features",
                f"A karakter {level}. szintről indul, ezért minden 1-{level}. szint közötti class/subclass feature-t ellenőrizni kell.",
                "level",
                True,
            ))
        return items

    def _role_checklist(self, role: str) -> List[CharacterCreationChecklistItem]:
        suggestions = self.ROLE_SUGGESTIONS.get(role, [])
        return [CharacterCreationChecklistItem(f"Role advice: {role}", suggestion, "role", False) for suggestion in suggestions]

    @staticmethod
    def _donjon_readiness_checklist(role: str) -> List[CharacterCreationChecklistItem]:
        return [
            CharacterCreationChecklistItem("Donjon readiness: scouting", "Trap-heavy dungeon esetén legyen Perception/Investigation és lehetőleg thieves' tools támogatás.", "donjon", False),
            CharacterCreationChecklistItem("Donjon readiness: sustain", "Ellenőrizd a healing, rest, light source, ration és resource recovery opciókat.", "donjon", False),
            CharacterCreationChecklistItem("Donjon readiness: role coverage", "Nézd meg, hogy a partyban van-e frontliner, scout, support/healer és ranged/control opció.", "donjon", False),
        ]

    @staticmethod
    def _sandbox_readiness_checklist() -> List[CharacterCreationChecklistItem]:
        return [
            CharacterCreationChecklistItem("Sandbox readiness: hooks", "Adj a karakternek legalább egy személyes célt, kapcsolatot és konfliktust.", "sandbox", False),
            CharacterCreationChecklistItem("Sandbox readiness: non-combat utility", "Legyen legalább egy erős nem-harci hozzájárulása: social, exploration, crafting, lore vagy downtime.", "sandbox", False),
        ]

    def _class_may_need_spell_review(self, class_name: str) -> bool:
        if not class_name:
            return False
        return class_name.strip().lower() in self.SPELLCASTER_CLASSES or self.spell_reference is not None and class_name.strip().lower() in self.SPELLCASTER_CLASSES

    @staticmethod
    def _build_advisory_text(advice: CharacterCreationAdvice) -> str:
        concept = f" — {advice.concept}" if advice.concept else ""
        lines = [f"Character creation advisory{concept}", f"Starting level: {advice.starting_level}", f"Preferred role: {advice.preferred_role}", ""]

        selected = []
        if advice.selected_class:
            selected.append(f"Class: {advice.selected_class}")
        if advice.selected_species:
            selected.append(f"Species: {advice.selected_species}")
        if advice.selected_background:
            selected.append(f"Background: {advice.selected_background}")
        if advice.selected_feat:
            selected.append(f"Feat: {advice.selected_feat}")
        if selected:
            lines.append("Választott opciók:")
            lines.extend(f"- {item}" for item in selected)
            lines.append("")

        if advice.missing_choices:
            lines.append("Hiányzó döntések:")
            lines.extend(f"- {item}" for item in advice.missing_choices)
            lines.append("")

        if advice.lookups:
            lines.append("Compendium lookup összefoglaló:")
            for lookup in advice.lookups:
                status = "found" if lookup.found else "missing"
                source = f" [{lookup.source}]" if lookup.source else ""
                name = lookup.top_match_name or lookup.query
                lines.append(f"- {lookup.label}: {name}{source} ({status})")
            lines.append("")

        lines.append("Teendők:")
        for item in advice.checklist:
            required = " [required]" if item.required else ""
            detail = f" — {item.detail}" if item.detail else ""
            lines.append(f"- {item.label}{required}{detail}")

        lines.append("")
        lines.append("Ez advisory lista; a végső döntés és karakterlap-frissítés a DM/player feladata.")
        return "\n".join(lines)
