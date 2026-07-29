from services.compendium.campaign_content_advisor import CampaignContentAdvisor
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType
from services.compendium.module_reference_service import ModuleReferenceQuery, ModuleReferenceService


def _advisor_with_lmop_shapes():
    raw = {
        "entries": [
            {
                "type": "entries",
                "name": "3. Trapped Hall",
                "entries": [
                    "This area was part of the original cellars, creating a hidden pit trap.",
                    {"type": "insetReadaloud", "entries": ["Thick dust covers the flagstones of this somber hallway."]},
                    "A character searching the hall spots the covered pit with a successful {@dc 15} Wisdom ({@skill Perception}) check.",
                    "On a failed save, the creature falls 20 feet, taking {@damage 2d6} bludgeoning damage and landing {@condition prone}.",
                    {"type": "entries", "name": "Awarding Experience Points", "entries": ["Divide 100 XP equally among the characters if the party avoids or survives the pit trap."]},
                ],
            },
            {
                "type": "entries",
                "name": "Important NPCs",
                "entries": [
                    {"type": "table", "rows": [["Toblen Stonehill", "Innkeeper."], ["Daran Edermath", "Member of the Order of the Gauntlet with a quest for the party."]]},
                ],
            },
        ]
    }
    index = CompendiumIndexService([
        CompendiumEntry(entry_id="adventure:lmop", name="Lost Mine Sample", entry_type=CompendiumEntryType.ADVENTURE, source="LMOP", raw=raw)
    ])
    return CampaignContentAdvisor(ModuleReferenceService(index))


def test_campaign_content_advisor_detects_trap_reward_and_entities():
    advisor = _advisor_with_lmop_shapes()

    advice = advisor.advise(ModuleReferenceQuery(text="Trapped Hall", module_name="Lost Mine"))

    assert advice.found is True
    assert advice.trap_hints
    assert advice.reward_hints
    entities = {entity for hint in advice.trap_hints + advice.reward_hints for entity in hint.extracted_entities}
    assert "DC 15" in entities
    assert "2d6" in entities
    assert "prone" in entities
    assert "100 XP" in entities
    assert any("trap" in item.lower() for item in advice.approval_checkpoints)
    assert any("xp" in item.lower() or "reward" in item.lower() for item in advice.approval_checkpoints)


def test_campaign_content_advisor_detects_npc_table_context():
    advisor = _advisor_with_lmop_shapes()

    advice = advisor.advise(ModuleReferenceQuery(text="Important NPCs", module_name="Lost Mine"))

    assert advice.found is True
    assert advice.npc_hints
    assert any("NPC" in hint.title or "Important NPCs" in hint.path_text for hint in advice.npc_hints)
