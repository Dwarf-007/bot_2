"""
SERVICES/COMPENDIUM/COMPENDIUM_INTEGRATION_SMOKE_GATE.PY
Aggregate smoke gate for the F1 compendium integration stack.

F1.9 purpose:
- Verify that F1.2-F1.8 work together as a dependency-light compendium stack.
- Build an in-memory mini 5etools-style raw directory.
- Exercise FiveEToolsDataSource, CompendiumIndexService, BestiaryService,
  RulesReferenceService, SpellReferenceService, CharacterOptionService, and
  LevelUpAdvisor.
- Verify the compendium layer remains advisory/reference-only and has no Avrae
  dispatch or Discord I/O coupling.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- No copyrighted/full-text response generation.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from services.bestiary_service import BestiaryService
from services.compendium.character_option_service import CharacterOptionService
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntryType
from services.compendium.fiveetools_data_source import FiveEToolsDataSource
from services.compendium.level_up_advisor import LevelUpAdvisor
from services.compendium.rules_reference_service import RulesReferenceService
from services.compendium.spell_reference_service import SpellReferenceService


CANONICAL_COMPENDIUM_FILES: tuple[str, ...] = (
    "services/compendium/compendium_models.py",
    "services/compendium/source_policy.py",
    "services/compendium/fiveetools_data_source.py",
    "services/compendium/compendium_index_service.py",
    "services/bestiary_service.py",
    "services/compendium/rules_reference_service.py",
    "services/compendium/spell_reference_service.py",
    "services/compendium/character_option_service.py",
    "services/compendium/level_up_advisor.py",
)

FORBIDDEN_RUNTIME_MARKERS: tuple[str, ...] = (
    "dispatch_commands",
    "AvraeDispatcher(",
    "AvraeClient(",
    ".is_available()",
    "message.channel.send",
)


@dataclass(frozen=True)
class CompendiumSmokeCheck:
    name: str
    ok: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CompendiumIntegrationSmokeResult:
    ok: bool
    checks: List[CompendiumSmokeCheck] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
            "stats": dict(self.stats),
        }

    def summary_text(self) -> str:
        passed = sum(1 for check in self.checks if check.ok)
        lines = [f"Compendium integration smoke gate: {passed}/{len(self.checks)} passed"]
        for check in self.checks:
            prefix = "OK" if check.ok else "FAIL"
            lines.append(f"- {prefix} {check.name}: {check.message}".rstrip())
        return "
".join(lines)


class CompendiumIntegrationSmokeGate:
    """Runs the aggregate F1 compendium smoke gate."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)

    def run(self) -> CompendiumIntegrationSmokeResult:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root = Path(tmp) / "raw"
            self._write_fixture_raw_data(raw_root)
            return self._run_against_raw_root(raw_root)

    def run_against_raw_root(self, raw_root: str | Path) -> CompendiumIntegrationSmokeResult:
        return self._run_against_raw_root(Path(raw_root))

    def _run_against_raw_root(self, raw_root: Path) -> CompendiumIntegrationSmokeResult:
        checks: List[CompendiumSmokeCheck] = []

        data_source = FiveEToolsDataSource(raw_root=raw_root)
        entries = data_source.load_entries()
        summary = data_source.load_summary()
        index = CompendiumIndexService(entries)
        stats = index.stats()

        checks.append(CompendiumSmokeCheck(
            name="fiveetools_data_source_loaded_entries",
            ok=len(entries) >= 8 and summary.ok,
            message="FiveEToolsDataSource loaded fixture entries." if len(entries) >= 8 and summary.ok else "FiveEToolsDataSource did not load expected entries.",
            details={"entries": len(entries), "summary": asdict(summary)},
        ))
        checks.append(CompendiumSmokeCheck(
            name="compendium_index_built",
            ok=stats.entries == len(entries) and stats.entries >= 8,
            message="CompendiumIndexService indexed loaded entries." if stats.entries == len(entries) and stats.entries >= 8 else "Compendium index stats are unexpected.",
            details={"stats": asdict(stats)},
        ))

        bestiary = BestiaryService(compendium_raw_root=raw_root)
        goblin = bestiary.get_monster_stats("Goblin")
        checks.append(CompendiumSmokeCheck(
            name="bestiary_service_compendium_lookup",
            ok=bool(goblin and goblin.get("name") == "Goblin" and goblin.get("hp", {}).get("average") == 7),
            message="BestiaryService resolved Goblin through compendium raw data." if goblin else "BestiaryService failed to resolve Goblin.",
            details={"monster": goblin or {}},
        ))

        rules = RulesReferenceService(index)
        grappled = rules.lookup("Grappled")
        checks.append(CompendiumSmokeCheck(
            name="rules_reference_condition_lookup",
            ok=grappled.found and grappled.matches[0].name == "Grappled" and "speed becomes 0" in grappled.matches[0].snippet,
            message="RulesReferenceService resolved Grappled condition." if grappled.found else "RulesReferenceService failed to resolve Grappled.",
            details={"advisory_text": grappled.advisory_text},
        ))

        spells = SpellReferenceService(index)
        fireball = spells.lookup("Fireball")
        checks.append(CompendiumSmokeCheck(
            name="spell_reference_lookup",
            ok=fireball.found and fireball.matches[0].name == "Fireball" and fireball.matches[0].level == 3,
            message="SpellReferenceService resolved Fireball metadata." if fireball.found else "SpellReferenceService failed to resolve Fireball.",
            details={"advisory_text": fireball.advisory_text},
        ))

        character_options = CharacterOptionService(index)
        fighter = character_options.lookup_class("Fighter")
        features = character_options.get_class_level_features("Fighter", 5)
        checks.append(CompendiumSmokeCheck(
            name="character_option_class_and_feature_lookup",
            ok=fighter.found and features.found and any(feature.name == "Extra Attack" for feature in features.features),
            message="CharacterOptionService resolved Fighter and level 5 feature." if fighter.found and features.found else "CharacterOptionService failed class/feature lookup.",
            details={"features": [asdict(feature) for feature in features.features]},
        ))

        level_up = LevelUpAdvisor(character_options, spell_reference=spells).build_level_up_advice("Aric", "Fighter", 4, 5)
        checks.append(CompendiumSmokeCheck(
            name="level_up_advisor_checklist",
            ok=any(item.label == "Level 5: Extra Attack" for item in level_up.checklist) and "Character sheet update" in [item.label for item in level_up.checklist],
            message="LevelUpAdvisor produced a level-up checklist." if level_up.checklist else "LevelUpAdvisor checklist is empty.",
            details={"advisory_text": level_up.advisory_text},
        ))

        missing, violations = self._scan_no_runtime_coupling(CANONICAL_COMPENDIUM_FILES, FORBIDDEN_RUNTIME_MARKERS)
        checks.append(CompendiumSmokeCheck(
            name="canonical_compendium_files_present",
            ok=not missing,
            message="All canonical compendium files are present." if not missing else "Some canonical compendium files are missing.",
            details={"missing": missing},
        ))
        checks.append(CompendiumSmokeCheck(
            name="no_avrae_or_discord_runtime_coupling",
            ok=not violations,
            message="No Avrae/Discord runtime markers found in canonical compendium files." if not violations else "Forbidden runtime markers found.",
            details={"violations": violations},
        ))

        result_stats = {
            "entries": stats.entries,
            "names": stats.names,
            "aliases": stats.aliases,
            "entry_types": dict(stats.entry_types),
            "raw_root": str(raw_root),
        }
        return CompendiumIntegrationSmokeResult(ok=all(check.ok for check in checks), checks=checks, stats=result_stats)

    def _scan_no_runtime_coupling(self, files: Iterable[str], markers: Iterable[str]) -> tuple[List[str], List[Dict[str, str]]]:
        missing: List[str] = []
        violations: List[Dict[str, str]] = []
        for rel_path in files:
            path = self.project_root / rel_path
            if not path.exists():
                missing.append(rel_path)
                continue
            text = path.read_text(encoding="utf-8")
            for marker in markers:
                if marker in text:
                    violations.append({"file": rel_path, "marker": marker})
        return missing, violations

    @staticmethod
    def _write_fixture_raw_data(raw_root: Path) -> None:
        (raw_root / "monsters").mkdir(parents=True, exist_ok=True)
        (raw_root / "spells").mkdir(parents=True, exist_ok=True)
        (raw_root / "conditions").mkdir(parents=True, exist_ok=True)
        (raw_root / "rules").mkdir(parents=True, exist_ok=True)
        (raw_root / "classes").mkdir(parents=True, exist_ok=True)
        (raw_root / "backgrounds").mkdir(parents=True, exist_ok=True)
        (raw_root / "species").mkdir(parents=True, exist_ok=True)
        (raw_root / "feats").mkdir(parents=True, exist_ok=True)

        _write_json(raw_root / "monsters" / "bestiary-mm.json", {
            "monster": [{
                "name": "Goblin",
                "source": "MM",
                "page": 166,
                "hp": {"average": 7},
                "ac": 15,
                "cr": "1/4",
                "action": [{"name": "Scimitar", "desc": "Melee Weapon Attack: +4 to hit. Hit: 1d6+2 slashing damage."}],
            }]
        })
        _write_json(raw_root / "spells" / "spells-phb.json", {
            "spell": [{
                "name": "Fireball",
                "source": "PHB",
                "page": 241,
                "level": 3,
                "school": "V",
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "point", "distance": {"amount": 150, "type": "feet"}},
                "duration": [{"type": "instant"}],
                "components": {"v": True, "s": True, "m": "a tiny ball of bat guano and sulfur"},
                "entries": ["A bright streak flashes from your pointing finger."],
            }]
        })
        _write_json(raw_root / "conditions" / "conditionsdiseases.json", {
            "condition": [{
                "name": "Grappled",
                "source": "PHB",
                "page": 290,
                "entries": ["A grappled creature's speed becomes 0, and it can't benefit from any bonus to its speed."],
            }]
        })
        _write_json(raw_root / "rules" / "actions.json", {
            "action": [{
                "name": "Dash",
                "source": "PHB",
                "entries": ["When you take the Dash action, you gain extra movement for the current turn."],
            }]
        })
        _write_json(raw_root / "classes" / "class-fighter.json", {
            "class": [{
                "name": "Fighter",
                "source": "PHB",
                "classFeatures": [
                    {"name": "Ability Score Improvement", "level": 4, "entries": ["Increase ability scores or choose a feat."]},
                    {"name": "Extra Attack", "level": 5, "entries": ["Attack twice when you take the Attack action."]},
                ],
            }],
            "classFeature": [{
                "name": "Action Surge",
                "source": "PHB",
                "className": "Fighter",
                "level": 2,
                "entries": ["Take one additional action."],
            }],
        })
        _write_json(raw_root / "backgrounds" / "backgrounds.json", {
            "background": [{"name": "Soldier", "source": "PHB", "entries": ["A military background."]}]
        })
        _write_json(raw_root / "species" / "races.json", {
            "race": [{"name": "Human", "source": "PHB", "entries": ["A versatile species."]}]
        })
        _write_json(raw_root / "feats" / "feats.json", {
            "feat": [{"name": "Alert", "source": "PHB", "entries": ["Always on the lookout for danger."]}]
        })


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
