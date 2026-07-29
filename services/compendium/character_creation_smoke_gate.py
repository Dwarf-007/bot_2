"""
SERVICES/COMPENDIUM/CHARACTER_CREATION_SMOKE_GATE.PY
Aggregate smoke gate for the F2 CharacterCreationAdvisor MVP.

F2.2 purpose:
- Verify that CharacterCreationAdvisor works with the F1/F2 compendium stack.
- Build a dependency-light fixture index.
- Exercise sandbox and donjon character creation advisory paths.
- Verify missing-choice reporting.
- Verify spellcaster review behavior.
- Verify no Avrae/Discord runtime coupling exists in character creation services.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No D&D Beyond integration.
- No LLM calls.
- No database dependency.
- Does not mutate character sheets.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

from services.compendium.character_creation_advisor import (
    CharacterBuildRole,
    CharacterCreationAdvisor,
    CharacterCreationRequest,
)
from services.compendium.character_option_service import CharacterOptionService
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.fiveetools_data_source import FiveEToolsDataSource
from services.compendium.rules_reference_service import RulesReferenceService
from services.compendium.spell_reference_service import SpellReferenceService


CANONICAL_CHARACTER_CREATION_FILES: tuple[str, ...] = (
    "services/compendium/character_creation_advisor.py",
    "services/compendium/character_option_service.py",
    "services/compendium/level_up_advisor.py",
    "services/compendium/spell_reference_service.py",
    "services/compendium/rules_reference_service.py",
    "services/compendium/compendium_index_service.py",
    "services/compendium/fiveetools_data_source.py",
)

FORBIDDEN_RUNTIME_MARKERS: tuple[str, ...] = (
    "dispatch_commands",
    "AvraeDispatcher(",
    "AvraeClient(",
    ".is_available()",
    "message.channel.send",
)


@dataclass(frozen=True)
class CharacterCreationSmokeCheck:
    name: str
    ok: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CharacterCreationSmokeResult:
    ok: bool
    checks: List[CharacterCreationSmokeCheck] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
            "stats": dict(self.stats),
        }

    def summary_text(self) -> str:
        passed = sum(1 for check in self.checks if check.ok)
        lines = [f"CharacterCreationAdvisor smoke gate: {passed}/{len(self.checks)} passed"]
        for check in self.checks:
            prefix = "OK" if check.ok else "FAIL"
            lines.append(f"- {prefix} {check.name}: {check.message}".rstrip())
        return "\n".join(lines)


class CharacterCreationSmokeGate:
    """Runs a dependency-light aggregate smoke for CharacterCreationAdvisor."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)

    def run(self) -> CharacterCreationSmokeResult:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root = Path(tmp) / "raw"
            self._write_fixture_raw_data(raw_root)
            return self.run_against_raw_root(raw_root)

    def run_against_raw_root(self, raw_root: str | Path) -> CharacterCreationSmokeResult:
        raw_root = Path(raw_root)
        checks: List[CharacterCreationSmokeCheck] = []

        entries = FiveEToolsDataSource(raw_root=raw_root).load_entries()
        index = CompendiumIndexService(entries)
        index_stats = index.stats()
        character_options = CharacterOptionService(index)
        spell_reference = SpellReferenceService(index)
        rules_reference = RulesReferenceService(index)
        advisor = CharacterCreationAdvisor(
            character_options=character_options,
            spell_reference=spell_reference,
            rules_reference=rules_reference,
        )

        checks.append(CharacterCreationSmokeCheck(
            name="fixture_entries_loaded",
            ok=index_stats.entries >= 7,
            message="Fixture compendium entries loaded and indexed." if index_stats.entries >= 7 else "Not enough fixture entries were indexed.",
            details={"stats": asdict(index_stats)},
        ))

        scout = advisor.build_advice(CharacterCreationRequest(
            concept="dungeon scout",
            starting_level=1,
            selected_class="Rogue",
            selected_species="Human",
            selected_background="Soldier",
            preferred_role=CharacterBuildRole.SCOUT,
            ability_score_method="standard array",
            include_donjon_readiness=True,
        ))
        scout_labels = [item.label for item in scout.checklist]
        checks.append(CharacterCreationSmokeCheck(
            name="donjon_scout_advice",
            ok=(not scout.missing_choices and any(label.startswith("Role advice: scout") for label in scout_labels) and "Donjon readiness: scouting" in scout_labels),
            message="Advisor produced donjon scout advice." if scout.checklist else "Donjon scout advice failed.",
            details={"advisory_text": scout.advisory_text},
        ))

        sandbox = advisor.build_advice(CharacterCreationRequest(
            concept="sandbox guard captain",
            starting_level=1,
            selected_class="Fighter",
            selected_species="Human",
            selected_background="Soldier",
            preferred_role=CharacterBuildRole.FRONTLINER,
            ability_score_method="point buy",
            include_sandbox_readiness=True,
        ))
        checks.append(CharacterCreationSmokeCheck(
            name="sandbox_frontliner_advice",
            ok=any(item.category == "sandbox" for item in sandbox.checklist) and any(item.category == "role" for item in sandbox.checklist),
            message="Advisor produced sandbox/frontliner readiness advice." if sandbox.checklist else "Sandbox advice failed.",
            details={"advisory_text": sandbox.advisory_text},
        ))

        wizard = advisor.build_advice(CharacterCreationRequest(
            concept="arcane utility caster",
            starting_level=1,
            selected_class="Wizard",
            selected_species="Human",
            selected_background="Soldier",
            preferred_role=CharacterBuildRole.UTILITY,
            ability_score_method="standard array",
            include_spell_review=True,
        ))
        checks.append(CharacterCreationSmokeCheck(
            name="spellcaster_review_advice",
            ok=any(item.label == "Spellcasting review" for item in wizard.checklist),
            message="Advisor added spellcasting review for Wizard." if wizard.checklist else "Spellcaster review failed.",
            details={"advisory_text": wizard.advisory_text},
        ))

        incomplete = advisor.build_advice(CharacterCreationRequest(concept="mystery hero"))
        checks.append(CharacterCreationSmokeCheck(
            name="missing_choice_reporting",
            ok={"class", "species", "background", "ability_score_method"}.issubset(set(incomplete.missing_choices)),
            message="Advisor reported missing core character creation choices." if incomplete.missing_choices else "Missing choices were not reported.",
            details={"missing_choices": list(incomplete.missing_choices)},
        ))

        missing_files, violations = self._scan_no_runtime_coupling(CANONICAL_CHARACTER_CREATION_FILES, FORBIDDEN_RUNTIME_MARKERS)
        checks.append(CharacterCreationSmokeCheck(
            name="canonical_character_creation_files_present",
            ok=not missing_files,
            message="All canonical character creation files are present." if not missing_files else "Some canonical character creation files are missing.",
            details={"missing_files": missing_files},
        ))
        checks.append(CharacterCreationSmokeCheck(
            name="no_avrae_or_discord_runtime_coupling",
            ok=not violations,
            message="No Avrae/Discord runtime markers found in CharacterCreationAdvisor path." if not violations else "Forbidden runtime markers found.",
            details={"violations": violations},
        ))

        result_stats = {
            "entries": index_stats.entries,
            "entry_types": dict(index_stats.entry_types),
            "raw_root": str(raw_root),
        }
        return CharacterCreationSmokeResult(ok=all(check.ok for check in checks), checks=checks, stats=result_stats)

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
        (raw_root / "classes").mkdir(parents=True, exist_ok=True)
        (raw_root / "species").mkdir(parents=True, exist_ok=True)
        (raw_root / "backgrounds").mkdir(parents=True, exist_ok=True)
        (raw_root / "feats").mkdir(parents=True, exist_ok=True)
        (raw_root / "spells").mkdir(parents=True, exist_ok=True)
        (raw_root / "conditions").mkdir(parents=True, exist_ok=True)

        _write_json(raw_root / "classes" / "class-rogue.json", {
            "class": [{"name": "Rogue", "source": "PHB", "entries": ["A skillful expert and scout."]}],
            "classFeature": [{"name": "Sneak Attack", "source": "PHB", "className": "Rogue", "level": 1, "entries": ["Deal extra damage when you have advantage or an ally nearby."]}],
        })
        _write_json(raw_root / "classes" / "class-fighter.json", {
            "class": [{"name": "Fighter", "source": "PHB", "entries": ["A master of martial combat."]}],
        })
        _write_json(raw_root / "classes" / "class-wizard.json", {
            "class": [{"name": "Wizard", "source": "PHB", "entries": ["A scholarly arcane spellcaster."]}],
        })
        _write_json(raw_root / "species" / "races.json", {
            "race": [{"name": "Human", "source": "PHB", "entries": ["A versatile species."]}],
        })
        _write_json(raw_root / "backgrounds" / "backgrounds.json", {
            "background": [{"name": "Soldier", "source": "PHB", "entries": ["A military background."]}],
        })
        _write_json(raw_root / "feats" / "feats.json", {
            "feat": [{"name": "Alert", "source": "PHB", "entries": ["Always alert to danger."]}],
        })
        _write_json(raw_root / "spells" / "spells-phb.json", {
            "spell": [{"name": "Mage Hand", "source": "PHB", "level": 0, "entries": ["A spectral hand appears."]}],
        })
        _write_json(raw_root / "conditions" / "conditionsdiseases.json", {
            "condition": [{"name": "Grappled", "source": "PHB", "entries": ["A grappled creature's speed becomes 0."]}],
        })


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
