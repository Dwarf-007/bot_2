from pathlib import Path

from services.compendium.character_creation_advisor import CharacterCreationAdvisor, CharacterCreationRequest
from services.compendium.character_option_service import CharacterOptionService
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType


def test_character_creation_advisor_smoke_with_minimal_index():
    index = CompendiumIndexService([
        CompendiumEntry(entry_id="class:fighter:phb", name="Fighter", entry_type=CompendiumEntryType.CLASS, source="PHB"),
        CompendiumEntry(entry_id="species:human:phb", name="Human", entry_type=CompendiumEntryType.SPECIES, source="PHB"),
        CompendiumEntry(entry_id="background:soldier:phb", name="Soldier", entry_type=CompendiumEntryType.BACKGROUND, source="PHB"),
    ])
    advisor = CharacterCreationAdvisor(CharacterOptionService(index))

    advice = advisor.build_advice(CharacterCreationRequest(
        concept="sandbox guard captain",
        selected_class="Fighter",
        selected_species="Human",
        selected_background="Soldier",
        preferred_role="frontliner",
        ability_score_method="standard array",
        include_sandbox_readiness=True,
    ))

    assert advice.lookups
    assert advice.checklist
    assert advice.advisory_text
    assert any(item.category == "role" for item in advice.checklist)
    assert any(item.category == "sandbox" for item in advice.checklist)


def test_character_creation_advisor_has_no_runtime_coupling_markers():
    text = Path("services/compendium/character_creation_advisor.py").read_text(encoding="utf-8")

    assert "dispatch_commands" not in text
    assert "AvraeDispatcher" not in text
    assert "AvraeClient" not in text
    assert ".is_available()" not in text
    assert "message.channel.send" not in text
