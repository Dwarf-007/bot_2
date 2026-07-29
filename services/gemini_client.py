"""
GEMINI_CLIENT.PY

Gemini API wrapper with:
- stable prompt assembly
- model fallback
- API key rotation
- normalized raw text retrieval
"""

import os
import time
from typing import Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError


CANONICAL_RESPONSE_CONTRACT = """
KÖTELEZŐ KIMENETI SZABÁLY:
A válaszod KIZÁRÓLAG egyetlen tiszta JSON objektum lehet.
NE használj markdown kódblokkot.
NE írj magyarázatot a JSON elé vagy mögé.
NE használj külön tageket, mint [XP_REWARD], [INVENTORY_UPDATE], [SECRET_TO].

A JSON séma pontosan ez:
{
  "narrative": "A játékosoknak szánt végső, tiszta narráció magyarul.",
  "required_check": "Perception | Investigation | Stealth | None",
  "dc": 0,
  "next_room_id": null,
  "xp_reward": 0,
  "milestone_reached": false,
  "inventory_update": {
    "gold": 0.0,
    "items": {},
    "ammo": {}
  },
  "avrae_sync_damage": null,
  "secret_messages": [
    {
      "player_id": "123456789",
      "text": "Titkos információ csak neki."
    }
  ],
  "rest_consequence": {
    "rest_type": "SHORT | LONG | NONE",
    "status": "SUCCESS | INTERRUPTED | NONE",
    "ambush_monster": null
  }
}

TOVÁBBI SZABÁLYOK:
- Ha nincs releváns adat, használj alapértelmezett értéket.
- A "narrative" legyen játékosoknak küldhető tiszta szöveg.
- A "secret_messages" NEM kerülhet be a narrative mezőbe.
- A "next_room_id" csak akkor legyen kitöltve, ha a mozgás érvényes.
- A "dc" legyen 0, ha nincs dobáskérés.
- A "required_check" legyen "None", ha nincs szükséges dobás.
""".strip()


class GeminiClientService:
    """
    Handles communication with Gemini and enforces a stable JSON response
    contract.
    """

    def __init__(self) -> None:
        raw_keys = os.getenv("GOOGLE_API_KEYS", "")
        self.api_keys = [key.strip() for key in raw_keys.split(",") if key.strip()]
        self.primary_model = "gemini-2.0-flash"
        self.fallback_model = "gemini-1.5-flash"

        if not self.api_keys:
            raise ValueError("GOOGLE_API_KEYS environment variable is empty.")

        self._active_key_index = 0

    def _get_client(self) -> genai.Client:
        """Returns a Gemini client using the currently active API key."""
        return genai.Client(api_key=self.api_keys[self._active_key_index])

    def _rotate_key(self) -> None:
        """Moves to the next API key in circular order."""
        self._active_key_index = (self._active_key_index + 1) % len(self.api_keys)

    def _build_system_instruction(
        self,
        mode: str,
        game_state: str,
        context_data: str,
        available_exits: str,
    ) -> str:
        """
        Builds a stable system instruction for the Dungeon Master model.
        """
        return f"""
Te egy sötét tónusú Dungeon Master vagy.
A játék nyelve magyar.
Soha ne dönts a játékos helyett.
Soha ne generálj markdownot vagy kommentárt.
Mindig kizárólag az előírt JSON objektumot add vissza.

[JÁTÉK MÓD]
- mode: {mode}
- game_state: {game_state}

[HELYSZÍN TÉNYEK]
{context_data}

[LEHETSÉGES KIJÁRATOK]
{available_exits}

{CANONICAL_RESPONSE_CONTRACT}
""".strip()

    async def generate_dm_response(
        self,
        mode: str,
        game_state: str,
        player_name: str,
        message_content: str,
        context_data: str,
        available_exits: str,
        model_name: Optional[str] = None,
    ) -> str:
        """
        Calls Gemini and returns raw text that should represent a single JSON
        object.
        """
        effective_model = model_name or self.primary_model

        system_instruction = self._build_system_instruction(
            mode=mode,
            game_state=game_state,
            context_data=context_data,
            available_exits=available_exits,
        )

        user_input = f"""
[JÁTÉKOS]
{player_name}

[JÁTÉKOS ÜZENETE]
{message_content}
""".strip()

        last_error: Optional[Exception] = None

        for _ in range(max(1, len(self.api_keys) * 2)):
            try:
                client = self._get_client()
                
                # Konfiguráció összeállítása a hivatalos google-genai formátum szerint
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                )

                response = client.models.generate_content(
                    model=effective_model,
                    contents=user_input,
                    config=config
                )

                text = getattr(response, "text", None)
                if not text or not text.strip():
                    raise ValueError("Gemini response did not contain text output.")

                return text.strip()

            except APIError as error:
                last_error = error
                status_code = getattr(error, "status_code", None)

                if status_code in (429, 503):
                    self._rotate_key()
                    if effective_model == self.primary_model:
                        effective_model = self.fallback_model
                    time.sleep(1)
                    continue

                raise
            except Exception as error:
                last_error = error
                self._rotate_key()
                if effective_model == self.primary_model:
                    effective_model = self.fallback_model

        raise RuntimeError(f"Gemini generation failed after retries: {last_error}")

