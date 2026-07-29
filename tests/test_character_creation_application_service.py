from core.turn_output import TurnOutput
from services.compendium.character_creation_advisor import CharacterBuildRole, CharacterCreationAdvisor, CharacterCreationRequest
from services.compendium.character_creation_application_service import (
    CharacterCreationApplicationRequest,
    CharacterCreationApplicationService,
    CharacterCreationTurnOutputMapper,
)
from services.compendium.character_option_service import CharacterOptionService
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType
from services.compendium.spell_reference_service import SpellReferenceService


def _service():
    index = CompendiumIndexService([
        CompendiumEntry(entry_id="class:rogue:phb", name="Rogue", entry_type=CompendiumEntryType.CLASS, source="PHB", summary="A skillful scout."),
        CompendiumEntry(entry_id="class:wizard:phb", name="Wizard", entry_type=CompendiumEntryType.CLASS, source="PHB", summary="An arcane spellcaster."),
        CompendiumEntry(entry_id="species:human:phb", name="Human", entry_type=CompendiumEntryType.SPECIES, source="PHB", summary="A versatile species."),
        CompendiumEntry(entry_id="background:soldier:phb", name="Soldier", entry_type=CompendiumEntryType.BACKGROUND, source="PHB", summary="A military background."),
        CompendiumEntry(entry_id="spell:mage-hand:phb", name="Mage Hand", entry_type=CompendiumEntryType.SPELL, source="PHB", raw={"level": 0, "entries": ["A spectral hand appears."]}),
    ])
    advisor = CharacterCreationAdvisor(CharacterOptionService(index), spell_reference=SpellReferenceService(index))
    return CharacterCreationApplicationService(advisor)


def test_application_service_maps_advice_to_turn_output():
    service = _service()

    output = service.advise(CharacterCreationApplicationRequest(
        concept="dungeon scout",
        selected_class="Rogue",
        selected_species="Human",
        selected_background="Soldier",
        preferred_role=CharacterBuildRole.SCOUT,
        ability_score_method="standard array",
        include_donjon_readiness=True,
        requester_id="u1",
        channel_id="c1",
    ))

    assert isinstance(output, TurnOutput)
    assert "Character Creation Advisory" in output.public_narrative
    assert "Rogue" in output.public_narrative
    assert "Donjon readiness" in output.public_narrative
    assert output.suggested_commands == []
    assert output.avrae_commands == []
    assert any("advisory only" in item for item in output.dm_instructions)
    assert "Requester ID: u1" in output.debug_notes
    assert "Channel ID: c1" in output.debug_notes


def test_application_service_accepts_advisor_request():
    service = _service()

    output = service.advise(CharacterCreationRequest(
        selected_class="Rogue",
        selected_species="Human",
        selected_background="Soldier",
        preferred_role="scout",
        ability_score_method="point buy",
    ))

    assert "Rogue" in output.public_narrative
    assert output.suggested_commands == []


def test_application_service_accepts_mapping_payload_with_alias_keys():
    service = _service()

    output = service.advise({
        "concept": "arcane utility",
        "class": "Wizard",
        "race": "Human",
        "background": "Soldier",
        "role": "utility",
        "ability_score_method": "standard array",
        "include_spell_review": True,
    })

    assert "Wizard" in output.public_narrative
    assert "Spellcasting review" in output.public_narrative
    assert output.suggested_commands == []


def test_turn_output_mapper_reports_missing_choices_in_public_narrative_and_dm_instructions():
    service = _service()

    output = service.advise(CharacterCreationApplicationRequest(concept="mystery hero"))

    assert "Missing required decisions" in output.public_narrative
    assert "class" in output.public_narrative
    assert any("Resolve missing required decisions" in item for item in output.dm_instructions)
    assert output.suggested_commands == []
