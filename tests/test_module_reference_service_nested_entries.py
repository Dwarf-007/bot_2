from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType
from services.compendium.module_reference_service import ModuleReferenceService


def test_module_reference_service_lists_deep_content_nodes():
    index = CompendiumIndexService([
        CompendiumEntry(
            entry_id="adventure:deep",
            name="Deep Module",
            entry_type=CompendiumEntryType.ADVENTURE,
            source="TEST",
            raw={
                "data": [
                    {
                        "type": "section",
                        "name": "Chapter 1",
                        "entries": [
                            {
                                "type": "section",
                                "name": "Room A",
                                "entries": ["A small room with an old altar."],
                            }
                        ],
                    }
                ]
            },
        )
    ])
    service = ModuleReferenceService(index)

    nodes = service.list_content_nodes("Deep Module")
    node_names = [node.name for node in nodes]

    assert "Chapter 1" in node_names
    assert "Room A" in node_names
    assert any(node.path_text == "Deep Module > Chapter 1 > Room A" for node in nodes)


def test_module_reference_service_nested_text_search():
    index = CompendiumIndexService([
        CompendiumEntry(
            entry_id="adventure:deep",
            name="Deep Module",
            entry_type=CompendiumEntryType.ADVENTURE,
            source="TEST",
            raw={
                "entries": [
                    {
                        "name": "Hidden Shrine",
                        "entries": ["The shrine contains a sealed door and a puzzle inscription."],
                    }
                ]
            },
        )
    ])
    service = ModuleReferenceService(index)

    result = service.lookup("sealed door")

    assert result.found is True
    assert result.matches[0].match_reason == "text_contains"
    assert "sealed door" in result.matches[0].snippet
    assert result.matches[0].requires_dm_review is True
