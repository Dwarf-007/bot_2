"""
SERVICES/COMPENDIUM/CHARACTER_CREATION_RUNTIME_WIRING_SMOKE.PY
Runtime wiring smoke for CharacterCreationAdvisor application service.

F2.4 purpose:
- Verify that the F2.3 CharacterCreationApplicationService can be composed from
  the F1/F2 compendium stack in a runtime-like way.
- Provide a small composition helper usable by sandbox/donjon runtime smoke tests.
- Exercise dict payloads and application DTO payloads.
- Verify output is canonical TurnOutput and does not contain Avrae/Discord runtime coupling.

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
from typing import Any, Dict, Iterable, List, Optional

from core.turn_output import TurnOutput
from services.compendium.character_creation_advisor import CharacterBuildRole
from services.compendium.character_creation_application_service import (
    CharacterCreationApplicationRequest,
    CharacterCreationApplicationService,
)
from services.compendium.character_creation_advisor import CharacterCreationAdvisor
from services.compendium.character_option_service import CharacterOptionService
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.fiveetools_data_source import FiveEToolsDataSource
from services.compendium.rules_reference_service import RulesReferenceService
from services.compendium.spell_reference_service import SpellReferenceService


CANONICAL_RUNTIME_WIRING_FILES: tuple[str, ...] = (
    "services/compendium/character_creation_application_service.py",
    "services/compendium/character_creation_advisor.py",
    "services/compendium/character_option_service.py",
    "services/compendium/spell_reference_service.py",
    "services/compendium/rules_reference_service.py",
    "services/compendium/compendium_index_service.py",
    "services/compendium/fiveetools_data_source.py",
    "services/compendium/character_creation_runtime_wiring_smoke.py",
)

FORBIDDEN_RUNTIME_MARKERS: tuple[str, ...] = (
    "dispatch_commands",
    "AvraeDispatcher(",
    "AvraeClient(",
    ".is_available()",
    "message.channel.send",
)


@dataclass(frozen=True)
class CharacterCreationRuntimeComponents:
    raw_root: Path
    data_source: FiveEToolsDataSource
    index: CompendiumIndexService
    character_options: CharacterOptionService
    spell_reference: SpellReferenceService
    rules_reference: RulesReferenceService
    advisor: CharacterCreationAdvisor
    application_service: CharacterCreationApplicationService


@dataclass(frozen=True)
class CharacterCreationRuntimeSmokeCheck:
    name: str
    ok: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CharacterCreationRuntimeSmokeResult:
    ok: bool
    checks: List[CharacterCreationRuntimeSmokeCheck] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
            "stats": dict(self.stats),
        }

    def summary_text(self) -> str:
        passed = sum(1 for check in self.checks if check.ok)
        lines = [f"CharacterCreation runtime wiring smoke: {passed}/{len(self.checks)} passed"]
        for check in self.checks:
            prefix = "OK" if check.ok else "FAIL"
            lines.append(f"- {prefix} {check.name}: {check.message}".rstrip())
        return "
".join(lines)


class CharacterCreationRuntimeWiringBuilder:
    """Small composition helper for character creation runtime services."""

    def build(self, raw_root: str | Path) -> CharacterCreationRuntimeComponents:
        raw_path = Path(raw_root)
        data_source = FiveEToolsDataSource(raw_root=raw_path)
        entries = data_source.load_entries()
        index = CompendiumIndexService(entries)
        character_options = CharacterOptionService(index)
        spell_reference = SpellReferenceService(index)
        rules_reference = RulesReferenceService(index)
        advisor = CharacterCreationAdvisor(
            character_options=character_options,
            spell_reference=spell_reference,
            rules_reference=rules_reference,
        )
        application_service = CharacterCreationApplicationService(advisor)
        return CharacterCreationRuntimeComponents(
            raw_root=raw_path,
            data_source=data_source,
            index=index,
            character_options=character_options,
            spell_reference=spell_reference,
            rules_reference=rules_reference,
            advisor=advisor,
            application_service=application_service,
        )


class CharacterCreationRuntimeWiringSmoke:
    """Runs a runtime-like wiring smoke for CharacterCreationApplicationService."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)

    def run(self) -> CharacterCreationRuntimeSmokeResult:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root = Path(tmp) / "raw"
            self._write_fixture_raw_data(raw_root)
            return self.run_against_raw_root(raw_root)

    def run_against_raw_root(self, raw_root: str | Path) -> CharacterCreationRuntimeSmokeResult:
        checks: List[CharacterCreationRuntimeSmokeCheck] = []
        components = CharacterCreationRuntimeWiringBuilder().build(raw_root)
        stats = components.index.stats()

        checks.append(CharacterCreationRuntimeSmokeCheck(
            name="runtime_components_composed",
            ok=stats.entries >= 7 and components.application_service is not None,
            message="Runtime-like character creation components were composed." if stats.entries >= 7 else "Runtime component composition loaded too few entries.",
            details={"stats": asdict(stats)},
        ))

        donjon_output = components.application_service.advise(CharacterCreationApplicationRequest(
            concept="dungeon scout",
            selected_class="Rogue",
            selected_species="Human",
            selected_background="Soldier",
            preferred_role=CharacterBuildRole.SCOUT,
            ability_score_method="standard array",
            include_donjon_readiness=True,
            channel_id="c-donjon",
            requester_id="u-scout",
        ))
        checks.append(self._check_turn_output(
            name="donjon_runtime_turn_output",
            output=donjon_output,
            required_fragments=["Character Creation Advisory", "Rogue", "Donjon readiness"],
        ))

        sandbox_output = components.application_service.advise({
            "concept": "sandbox guard captain",
            "class": "Fighter",
            "race": "Human",
            "background": "Soldier",
            "role": "frontliner",
            "ability_score_method": "point buy",
            "include_sandbox_readiness": True,
            "audience": "dm",
        })
        checks.append(self._check_turn_output(
            name="sandbox_runtime_dict_payload_turn_output",
            output=sandbox_output,
            required_fragments=["Character Creation Advisory", "Fighter", "Sandbox readiness"],
        ))

        wizard_output = components.application_service.advise({
            "concept": "arcane utility",
            "class": "Wizard",
            "species": "Human",
            "background": "Soldier",
            "role": "utility",
            "ability_score_method": "standard array",
            "include_spell_review": True,
        })
        checks.append(self._check_turn_output(
            name="spellcaster_runtime_turn_output",
            output=wizard_output,
            required_fragments=["Wizard", "Spellcasting review"],
        ))

        incomplete_output = components.application_service.advise({"concept": "mystery hero"})
        checks.append(self._check_turn_output(
            name="incomplete_request_runtime_turn_output",
            output=incomplete_output,
            required_fragments=["Missing required decisions", "class", "species", "background"],
        ))

        missing_files, violations = self._scan_no_runtime_coupling(CANONICAL_RUNTIME_WIRING_FILES, FORBIDDEN_RUNTIME_MARKERS)
        checks.append(CharacterCreationRuntimeSmokeCheck(
            name="canonical_runtime_wiring_files_present",
            ok=not missing_files,
            message="All canonical F2 runtime wiring files are present." if not missing_files else "Some canonical runtime wiring files are missing.",
            details={"missing_files": missing_files},
        ))
        checks.append(CharacterCreationRuntimeSmokeCheck(
            name="no_avrae_or_discord_runtime_coupling",
            ok=not violations,
            message="No Avrae/Discord markers found in F2 runtime wiring path." if not violations else "Forbidden runtime markers found.",
            details={"violations": violations},
        ))

        result_stats = {
            "entries": stats.entries,
            "entry_types": dict(stats.entry_types),
            "raw_root": str(components.raw_root),
        }
        return CharacterCreationRuntimeSmokeResult(ok=all(check.ok for check in checks), checks=checks, stats=result_stats)

    @staticmethod
    def _check_turn_output(name: str, output: TurnOutput, required_fragments: List[str]) -> CharacterCreationRuntimeSmokeCheck:
        ok = (
            isinstance(output, TurnOutput)
            and bool(output.public_narrative.strip())
            and output.suggested_commands == []
            and output.avrae_commands == []
            and all(fragment in output.public_narrative for fragment in required_fragments)
            and bool(output.dm_instructions)
        )
        return CharacterCreationRuntimeSmokeCheck(
            name=name,
            ok=ok,
            message="Application service returned advisory TurnOutput." if ok else "Application service TurnOutput did not satisfy runtime contract.",
            details={
                "public_narrative": output.public_narrative,
                "dm_instructions": list(output.dm_instructions),
                "debug_notes": list(output.debug_notes),
            },
        )

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
        (raw_root / "spells").mkdir(parents=True, exist_ok=True)
        (raw_root / "conditions").mkdir(parents=True, exist_ok=True)

        _write_json(raw_root / "classes" / "class-rogue.json", {
            "class": [{"name": "Rogue", "source": "PHB", "entries": ["A skillful expert and scout."]}],
            "classFeature": [{"name": "Sneak Attack", "source": "PHB", "className": "Rogue", "level": 1, "entries": ["Deal extra damage."]}],
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
        _write_json(raw_root / "spells" / "spells-phb.json", {
            "spell": [{"name": "Mage Hand", "source": "PHB", "level": 0, "entries": ["A spectral hand appears."]}],
        })
        _write_json(raw_root / "conditions" / "conditionsdiseases.json", {
            "condition": [{"name": "Grappled", "source": "PHB", "entries": ["A grappled creature's speed becomes 0."]}],
        })


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
