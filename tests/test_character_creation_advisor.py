from services.compendium.character_creation_advisor import CharacterBuildRole, CharacterCreationAdvisor, CharacterCreationRequest
from services.compendium.character_option_service import CharacterOptionService
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType
from services.compendium.spell_reference_service import SpellReferenceService


def _index():
    return CompendiumIndexService([
        CompendiumEntry(entry_id="class:rogue:phb", name="Rogue", entry_type=CompendiumEntryType.CLASS, source="PHB", summary="A skillful expert and scout."),
        CompendiumEntry(entry_id="class:wizard:phb", name="Wizard", entry_type=CompendiumEntryType.CLASS, source="PHB", summary="A scholarly arcane spellcaster."),
        CompendiumEntry(entry_id="species:human:phb", name="Human", entry_type=CompendiumEntryType.SPECIES, source="PHB", summary="A versatile species."),
        CompendiumEntry(entry_id="background:soldier:phb", name="Soldier", entry_type=CompendiumEntryType.BACKGROUND, source="PHB", summary="A military background."),
        CompendiumEntry(entry_id="feat:alert:phb", name="Alert", entry_type=CompendiumEntryType.FEAT, source="PHB", summary="Always alert to danger."),
        CompendiumEntry(entry_id="spell:mage-hand:phb", name="Mage Hand", entry_type=CompendiumEntryType.SPELL, source="PHB", raw={"level": 0, "entries": ["A spectral hand appears."]}),
    ])


def test_character_creation_advisor_builds_full_advisory_for_scout():
    index = _index()
    advisor = CharacterCreationAdvisor(CharacterOptionService(index), spell_reference=SpellReferenceService(index))
    request = CharacterCreationRequest(
        concept="dungeon scout",
        starting_level=1,
        selected_class="Rogue",
        selected_species="Human",
        selected_background="Soldier",
        preferred_role=CharacterBuildRole.SCOUT,
        ability_score_method="standard array",
        include_donjon_readiness=True,
    )

    advice = advisor.build_advice(request)

    assert advice.concept == "dungeon scout"
    assert advice.preferred_role == "scout"
    assert advice.missing_choices == []
    assert any(lookup.label == "Class" and lookup.found for lookup in advice.lookups)
    labels = [item.label for item in advice.checklist]
    assert "Review level 1 class features" in labels
    assert any(label.startswith("Role advice: scout") for label in labels)
    assert "Donjon readiness: scouting" in labels
    assert "Character creation advisory" in advice.advisory_text
    assert "Rogue" in advice.advisory_text
    assert "advisory" in advice.advisory_text


def test_character_creation_advisor_reports_missing_required_choices():
    advisor = CharacterCreationAdvisor(CharacterOptionService(_index()))
    request = CharacterCreationRequest(concept="unknown hero")

    advice = advisor.build_advice(request)

    assert "class" in advice.missing_choices
    assert "species" in advice.missing_choices
    assert "background" in advice.missing_choices
    assert "ability_score_method" in advice.missing_choices
    assert any(item.required for item in advice.checklist)
    assert "Hiányzó döntések" in advice.advisory_text


def test_character_creation_advisor_adds_spell_review_for_spellcaster():
    index = _index()
    advisor = CharacterCreationAdvisor(CharacterOptionService(index), spell_reference=SpellReferenceService(index))
    request = CharacterCreationRequest(
        selected_class="Wizard",
        selected_species="Human",
        selected_background="Soldier",
        ability_score_method="point buy",
        include_spell_review=True,
    )

    advice = advisor.build_advice(request)

    assert any(item.label == "Spellcasting review" for item in advice.checklist)


def test_character_creation_advisor_supports_sandbox_readiness():
    advisor = CharacterCreationAdvisor(CharacterOptionService(_index()))
    request = CharacterCreationRequest(
        selected_class="Rogue",
        selected_species="Human",
        selected_background="Soldier",
        ability_score_method="rolled",
        include_sandbox_readiness=True,
    )

    advice = advisor.build_advice(request)

    assert any(item.category == "sandbox" for item in advice.checklist)
