
import random


class TargetingService:

    def select_targets(self, players, mode="random", count=1):

        if not players:
            return []

        if mode == "all":
            return players

        if mode == "random":
            return random.sample(players, min(count, len(players)))

        return players[:count]
