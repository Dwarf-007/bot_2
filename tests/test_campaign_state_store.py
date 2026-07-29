
from services.campaign.campaign_state_models import CampaignState, CampaignSnapshot
from services.campaign.campaign_state_store import CampaignStateStore

def test_store_roundtrip():
    s=CampaignState(campaign_id='c1', title='Sandbox')
    store=CampaignStateStore()
    store.save_campaign(s)
    assert store.get_campaign('c1') is s
    snap=CampaignSnapshot(snapshot_id='s1', campaign_id='c1', state=s)
    store.create_snapshot(snap)
    assert store.restore_snapshot('s1') is s
