
import json

class LLMResponseParser:

    @staticmethod
    def parse(text: str):

        try:
            data = json.loads(text)
        except:
            data = {}

        return type("Response", (), {
            "narrative": data.get("narrative"),
            "xp_reward": data.get("xp_reward", 0),
            "inventory_update": data.get("inventory_update", {}),
            "secret_messages": data.get("secret_messages", []),
            "avrae_sync_damage": data.get("avrae_sync_damage"),
            "required_check": data.get("required_check", "None"),
            "dc": data.get("dc", 0)
        })()
