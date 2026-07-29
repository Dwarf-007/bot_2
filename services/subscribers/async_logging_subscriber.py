
class AsyncLoggingSubscriber:
    """
    Async-safe logging subscriber.
    """

    async def on_state_changed(self, payload):
        print(
            f"[STATE] {payload['from']} → {payload['to']} "
            f"(event={payload['event']})"
        )

    async def on_combat_started(self, payload):
        print(
            f"[COMBAT] Started in room={payload.get('room_id')}"
        )

    async def on_player_moved(self, payload):
        print(
            f"[MOVE] {payload['from_room']} → {payload['to_room']}"
        )

