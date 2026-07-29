from core.turn_output import TurnOutput
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType
from services.compendium.module_reference_application_service import ModuleReferenceApplicationRequest, ModuleReferenceApplicationService
from services.compendium.module_reference_service import ModuleReferenceService


def _service():
    index = CompendiumIndexService([
        CompendiumEntry(
            entry_id="adventure:lmop",
            name="Lost Mine Sample",
            entry_type=CompendiumEntryType.ADVENTURE,
            source="LMOP",
            raw={
                "entries": [
                    {
                        "type": "entries",
                        "name": "Goblin Ambush",
                        "entries": [
                            "Four goblins are hiding in the woods and attack when someone approaches the bodies.",
                            {"type": "insetReadaloud", "entries": ["Two dead horses block the path ahead."]},
                        ],
                    },
                    {
                        "type": "entries",
                        "name": "Goblin Trail",
                        "entries": ["A hidden trail leads northwest toward Cragmaw hideout and includes traps."],
                    },
                ]
            },
        )
    ])
    return ModuleReferenceApplicationService(ModuleReferenceService(index))


def test_module_reference_application_service_maps_reference_to_turn_output():
    service = _service()

    output = service.advise(ModuleReferenceApplicationRequest(
        query="Goblin Ambush",
        module_name="Lost Mine",
        campaign_id="lmop-campaign",
        scene_id="road-ambush",
    ))

    assert isinstance(output, TurnOutput)
    assert "Module Reference Advisory" in output.public_narrative
    assert "Goblin Ambush" in output.public_narrative
    assert "DM should review" in output.public_narrative
    assert output.suggested_commands == []
    assert output.avrae_commands == []
    assert any("DM approval required" in item for item in output.dm_instructions)
    assert any("Reference snippet" in item for item in output.dm_instructions)


def test_module_reference_application_service_accepts_dict_payload_aliases():
    service = _service()

    output = service.advise({
        "location": "Goblin Trail",
        "module": "Lost Mine",
        "campaign_id": "lmop",
        "room_id": "trail-01",
        "include_player_summary": True,
    })

    assert "Goblin Trail" in output.public_narrative
    assert "Campaign: **lmop**" in output.public_narrative
    assert "Scene: **trail-01**" in output.public_narrative
    assert output.suggested_commands == []


def test_module_reference_application_service_handles_missing_reference():
    service = _service()

    output = service.advise("Unknown Section")

    assert "No module/campaign reference was found" in output.public_narrative
    assert any("broaden" in item.lower() or "clarify" in item.lower() for item in output.dm_instructions)
    assert output.suggested_commands == []
