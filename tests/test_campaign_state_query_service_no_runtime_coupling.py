from pathlib import Path


def test_campaign_state_query_service_has_no_runtime_coupling_or_mutation():
    text = Path('services/campaign/campaign_state_query_service.py').read_text(encoding='utf-8')

    assert 'dispatch_commands' not in text
    assert 'AvraeDispatcher' not in text
    assert 'AvraeClient' not in text
    assert '.is_available()' not in text
    assert 'message.channel.send' not in text
    assert 'TurnOutput' not in text
    assert '.save_campaign(' not in text
    assert 'apply_proposal' not in text
