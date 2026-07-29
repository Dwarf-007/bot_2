
async def process_structured_xp_and_level_up(
    channel,
    active_players,
    response,
    xp_mode,
    player_repo
):
    if response.xp_reward <= 0:
        return

    xp_each = response.xp_reward // max(len(active_players), 1)

    for p in active_players:
        player_repo.add_xp(channel.id, str(p), xp_each)
        await channel.send(f"<@{p}> kapott {xp_each} XP-t")
