from services.compendium.character_option_service import CharacterOptionService
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType
from services.compendium.level_up_advisor import LevelUpAdvisor
from services.compendium.spell_reference_service import SpellReferenceService


def _index():
    return CompendiumIndexService([
        CompendiumEntry(
            entry_id="class:fighter:phb",
            name="Fighter",
            entry_type=CompendiumEntryType.CLASS,
            source="PHB",
            raw={"classFeatures": [
                {"name": "Ability Score Improvement", "level": 4, "entries": ["Increase ability scores or choose a feat."]},
                {"name": "Extra Attack", "level": 5, "entries": ["Attack twice when taking the Attack action."]},
            ]},
        ),
        CompendiumEntry(
            entry_id="spell:fireball:phb",
            name="Fireball",
            entry_type=CompendiumEntryType.SPELL,
            source="PHB",
            raw={"level": 3, "entries": ["A bright streak flashes."]},
        ),
    ])


def test_level_up_advisor_builds_checklist_with_class_features():
    index = _index()
    advisor = LevelUpAdvisor(CharacterOptionService(index))

    advice = advisor.build_level_up_advice("Aric", "Fighter", 3, 5)

    assert advice.character_name == "Aric"
    assert advice.class_name == "Fighter"
    assert advice.from_level == 3
    assert advice.to_level == 5
    labels = [item.label for item in advice.checklist]
    assert "Level 4: Ability Score Improvement" in labels
    assert "Level 5: Extra Attack" in labels
    assert "HP update" in labels
    assert "Character sheet update" in labels
    assert "Fighter 3 → 5" in advice.advisory_text
    assert "advisory" in advice.advisory_text


def test_level_up_advisor_adds_spellcasting_review_when_spell_service_available():
    index = _index()
    advisor = LevelUpAdvisor(CharacterOptionService(index), spell_reference=SpellReferenceService(index))

    advice = advisor.build_level_up_advice("Mira", "Fighter", 4, 5)

    assert any(item.label == "Spellcasting review" for item in advice.checklist)


def test_level_up_advisor_handles_invalid_level_direction():
    advisor = LevelUpAdvisor(CharacterOptionService(_index()))

    advice = advisor.build_level_up_advice("Aric", "Fighter", 5, 5)

    assert any(item.label == "Ellenőrizd a szinteket" for item in advice.checklist)
