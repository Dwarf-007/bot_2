from pathlib import Path


def test_c3_05_handlers_do_not_dispatch_avrae():
    for file_name in [
        "services/combat_start_service.py",
        "services/combat_event_handler.py",
        "services/damage_event_handler.py",
    ]:
        text = Path(file_name).read_text(encoding="utf-8")
        assert "dispatch_commands" not in text
        assert "AvraeDispatcher" not in text
        assert "AvraeClient" not in text
        assert "urlopen" not in text
        assert "message.channel.send" not in text
