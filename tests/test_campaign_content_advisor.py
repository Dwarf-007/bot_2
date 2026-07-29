from services.compendium.campaign_content_advisor import CampaignContentAdvisor, CampaignContentKind
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType
from services.compendium.module_reference_service import ModuleReferenceQuery, ModuleReferenceService


def _service():
    index = CompendiumIndexService([
        CompendiumEntry(
            entry_id="adventure:lmop",
            name="Lost Mine Sample",
            entry_type=CompendiumEntryType.ADVENTURE,
            source="LMOP",
            raw={"entries": [
                {"type": "entries", "name": "Goblin Ambush", "entries": [
                    {"type": "insetReadaloud", "entries": ["Two dead horses block the path ahead."]},
                    "Four {@creature goblin||goblins} are hiding in the woods and then attack.",
                    "{@b Developments}",
                    "The characters might capture one or more goblins and learn where the trail leads.",
                ]},
                {"type": "entries", "name": "Treasure", "entries": ["The pouch contains 16 sp and 7 gp."]},
            ]},
        )
    ])
    return CampaignContentAdvisor(ModuleReferenceService(index))


def test_campaign_content_advisor_classifies_read_aloud_encounter_development_and_treasure():
    advisor = _service()

    advice = advisor.advise(ModuleReferenceQuery(text="Goblin Ambush", module_name="Lost Mine"))

    assert advice.found is True
    assert advice.read_aloud_candidates
    assert advice.encounter_hints
    assert advice.development_hints
    assert any("combat" in item.lower() or "starting combat" in item.lower() for item in advice.approval_checkpoints)
    assert any("read-aloud" in item.lower() for item in advice.approval_checkpoints)
    assert "Campaign content advisory" in advice.advisory_text


def test_campaign_content_advisor_handles_missing_query():
    advisor = _service()

    advice = advisor.advise("Unknown Room")

    assert advice.found is False
    assert advice.approval_checkpoints
    assert "No matching" in advice.advisory_text


def test_campaign_content_advisor_classify_nodes_directly():
    advisor = _service()
    nodes = advisor.module_reference.list_content_nodes("Lost Mine")

    hints = advisor.classify_nodes(nodes)
    kinds = {hint.kind for hint in hints}

    assert CampaignContentKind.READ_ALOUD in kinds
    assert CampaignContentKind.ENCOUNTER in kinds
    assert CampaignContentKind.TREASURE in kinds
