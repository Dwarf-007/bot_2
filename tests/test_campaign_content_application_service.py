from core.turn_output import TurnOutput
from services.compendium.campaign_content_advisor import CampaignContentAdvisor
from services.compendium.campaign_content_application_service import CampaignContentApplicationRequest, CampaignContentApplicationService
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType
from services.compendium.module_reference_service import ModuleReferenceQuery, ModuleReferenceService


def _service():
    raw = {
        "entries": [
            {"type": "entries", "name": "Goblin Ambush", "entries": [
                {"type": "insetReadaloud", "entries": ["Two dead horses block the path ahead."]},
                "Four {@creature goblin||goblins} are hiding in the woods and attack.",
                "{@b Developments}",
                "The characters might capture goblins and learn about the trail.",
            ]},
            {"type": "entries", "name": "3. Trapped Hall", "entries": [
                "A hidden pit trap lies under loose stone tiles.",
                "A successful {@dc 15} Wisdom ({@skill Perception}) check spots the trap.",
                "On a failed save, the creature takes {@damage 2d6} bludgeoning damage and lands {@condition prone}.",
                {"type": "entries", "name": "Awarding Experience Points", "entries": ["Divide 100 XP equally if the party survives."]},
            ]},
        ]
    }
    index = CompendiumIndexService([
        CompendiumEntry(entry_id="adventure:lmop", name="Lost Mine Sample", entry_type=CompendiumEntryType.ADVENTURE, source="LMOP", raw=raw)
    ])
    advisor = CampaignContentAdvisor(ModuleReferenceService(index))
    return CampaignContentApplicationService(advisor)


def test_campaign_content_application_service_maps_advice_to_turn_output():
    service = _service()

    output = service.advise(CampaignContentApplicationRequest(
        query="Goblin Ambush",
        module_name="Lost Mine",
        campaign_id="lmop",
        scene_id="ambush-001",
    ))

    assert isinstance(output, TurnOutput)
    assert "Campaign Content Advisory" in output.public_narrative
    assert "Read-aloud candidate" in output.public_narrative
    assert "DM-only content detected" in output.public_narrative
    assert output.suggested_commands == []
    assert output.avrae_commands == []
    assert any("Approval checkpoints" in item for item in output.dm_instructions)
    assert any("Encounter hints" in item for item in output.dm_instructions)


def test_campaign_content_application_service_accepts_dict_payload():
    service = _service()

    output = service.advise({
        "location": "Trapped Hall",
        "module": "Lost Mine",
        "campaign_id": "lmop",
        "room_id": "redbrand-03",
    })

    assert "Campaign: **lmop**" in output.public_narrative
    assert "Scene: **redbrand-03**" in output.public_narrative
    assert "trap mechanics" in output.public_narrative
    assert any("Trap hints" in item for item in output.dm_instructions)
    assert any("DC 15" in item for item in output.dm_instructions)
    assert output.suggested_commands == []


def test_campaign_content_application_service_accepts_module_reference_query():
    service = _service()

    output = service.advise(ModuleReferenceQuery(text="Goblin Ambush", module_name="Lost Mine"))

    assert "Goblin Ambush" in output.public_narrative
    assert output.suggested_commands == []


def test_campaign_content_application_service_handles_missing_result():
    service = _service()

    output = service.advise("Unknown Location")

    assert "No matching campaign content was found" in output.public_narrative
    assert any("No matching module node" in item for item in output.dm_instructions)
    assert output.suggested_commands == []
