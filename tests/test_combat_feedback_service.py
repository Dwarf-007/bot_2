from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.bootstrap import build_runtime
from core.game_events import EventTypes


def test_process_avrae_message_emits_player_roll_event():
    runtime = build_runtime()
    channel_id = "combat-test-channel"
    runtime.combat_feedback_service.register_encounter(
        channel_id=channel_id,
        room_id="room_1",
        monsters=[{"name": "Goblin", "count": 1}],
        xp_reward_total=50,
    )

    captured = []

    def capture_handler(event):
        captured.append(event.payload)

    runtime.event_bus.register(EventTypes.PLAYER_ROLL, capture_handler)

    message = SimpleNamespace(
        channel=SimpleNamespace(id=channel_id),
        content="Alice rolls 1d20+5 = 17 for her attack.",
        embeds=[],
        author=SimpleNamespace(name="Avrae", display_name="Avrae"),
    )

    result = asyncio.run(runtime.combat_feedback_service.process_avrae_message(message))

    assert len(result.roll_results) == 1
    assert result.roll_results[0]["actor"] == "Alice"
    assert result.roll_results[0]["formula"] == "1d20+5"
    assert result.roll_results[0]["total"] == 17
    assert captured and captured[0]["channel_id"] == channel_id
    assert captured[0]["actor"] == "Alice"
    assert captured[0]["total"] == 17
