from services.campaign.campaign_state_models import (
    CampaignState,
    LocationState,
    NpcState,
    QuestState,
    QuestStatus,
    CampaignWorldTruth,
)
from services.campaign.campaign_state_store import CampaignStateStore
from services.campaign.campaign_state_query_service import CampaignStateQueryService


def _store():
    state = CampaignState(campaign_id='c1', title='Sandbox', theme='mystery', tone='dark')
    state.locations['town'] = LocationState(location_id='town', name='Town', discovered=True, visited=True)
    state.locations['tower'] = LocationState(location_id='tower', name='Old Tower', discovered=True, visited=False)
    state.knowledge.known_locations.append('town')
    state.knowledge.known_locations.append('tower')
    state.npcs['innkeeper'] = NpcState(npc_id='innkeeper', name='Innkeeper')
    state.knowledge.known_npcs.append('innkeeper')
    state.quests['q1'] = QuestState(quest_id='q1', title='Missing Caravans', status=QuestStatus.ACTIVE)
    state.knowledge.known_clues.append('Smoke seen near the old tower.')
    state.world_truths.append(CampaignWorldTruth(truth_id='t1', summary='The king is dead.', revealed=False))
    store = CampaignStateStore()
    store.save_campaign(state)
    return store


def test_query_service_summarizes_campaign_state():
    service = CampaignStateQueryService(_store())

    summary = service.summarize('c1')

    assert summary.title == 'Sandbox'
    assert summary.theme == 'mystery'
    assert summary.known_locations == ['town', 'tower']
    assert summary.visited_locations == ['town']
    assert summary.known_npcs == ['innkeeper']
    assert summary.active_quests == ['q1']
    assert summary.known_clues == ['Smoke seen near the old tower.']
    assert summary.hidden_truth_count == 1


def test_query_service_lists_state_parts():
    service = CampaignStateQueryService(_store())

    assert [loc.location_id for loc in service.list_known_locations('c1')] == ['town', 'tower']
    assert [loc.location_id for loc in service.list_visited_locations('c1')] == ['town']
    assert [quest.quest_id for quest in service.list_active_quests('c1')] == ['q1']
    assert [npc.npc_id for npc in service.list_known_npcs('c1')] == ['innkeeper']
    assert service.list_known_clues('c1') == ['Smoke seen near the old tower.']


def test_query_service_handles_missing_campaign_safely():
    service = CampaignStateQueryService(CampaignStateStore())

    summary = service.summarize('missing')

    assert summary.campaign_id == 'missing'
    assert summary.title == ''
    assert service.list_known_locations('missing') == []
