from dataclasses import dataclass
from services.campaign.campaign_state_models import CampaignState, LocationState
from services.campaign.campaign_state_store import CampaignStateStore
from services.campaign.campaign_state_query_service import CampaignStateQueryService


@dataclass(frozen=True)
class FakeProgress:
    channel_id: str
    campaign_id: str
    current_scene_id: str
    current_room_id: str
    milestone: str


class FakeProgressRepo:
    def get_channel_progress(self, channel_id):
        return FakeProgress(channel_id=channel_id, campaign_id='c1', current_scene_id='s1', current_room_id='r1', milestone='entered')

    def list_objectives(self, channel_id):
        return ['objective-1']


class FakeLocationRepo:
    def get_room(self, room_id):
        return {'room_id': room_id, 'title': 'Room One'}

    def list_rooms(self, campaign_id):
        return [{'room_id': 'r1'}]


class FakeAliasRepo:
    def search_aliases(self, campaign_id, query, limit=1):
        class Rec:
            room_id = 'r1'
        return [Rec()]


def test_query_service_builds_runtime_context_with_repositories():
    store = CampaignStateStore()
    state = CampaignState(campaign_id='c1', title='Campaign')
    state.locations['r1'] = LocationState(location_id='r1', name='Room One', discovered=True, visited=True)
    store.save_campaign(state)
    service = CampaignStateQueryService(
        store,
        campaign_progress_repository=FakeProgressRepo(),
        location_repository=FakeLocationRepo(),
        room_alias_repository=FakeAliasRepo(),
    )

    context = service.get_runtime_context('c1', channel_id='ch1')

    assert context.current_scene_id == 's1'
    assert context.current_room_id == 'r1'
    assert context.active_location.name == 'Room One'
    assert context.repository_context['room_count'] == 1
    assert context.repository_context['open_objectives'] == ['objective-1']
    assert service.resolve_room_alias('c1', 'room one') == 'r1'
