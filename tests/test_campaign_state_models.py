from services.campaign.campaign_state_models import CampaignState, LocationState

def test_campaign_state_model():
    state=CampaignState(campaign_id='c1', title='Sandbox')
    state.locations['town']=LocationState(location_id='town', name='Town')
    assert state.locations['town'].name=='Town'
