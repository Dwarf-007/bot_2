"""
SERVICES/SUBSCRIBERS/LOGGING_SUBSCRIBER.PY

Simple debug logger subscriber.
"""

from __future__ import annotations


class LoggingSubscriber:
    """Simple debug logger subscriber."""

    def on_state_changed(self, payload):
        print(
            f"[STATE] {payload['from']} -> {payload['to']} "
            f"(event={payload['event']})"
        )

    def on_combat_started(self, payload):
        print(
            f"[COMBAT] Started in room={payload.get('room_id')}"
        )

    def on_player_moved(self, payload):
        print(
            f"[MOVE] {payload['from_room']} -> {payload['to_room']}"
        )
