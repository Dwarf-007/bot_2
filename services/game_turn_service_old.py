"""
SERVICES/GAME_TURN_SERVICE.PY
Sprint 11.6 update:
- Adds optional campaign_id_override to process().
- Smoke/debug runners can force a specific runtime campaign without needing to mutate channel state.
- Normal Discord flow remains unchanged.
"""
from __future__ import annotations
from typing import Optional

from core.turn_output import TurnOutput
from llm.llm_response_parser import LLMResponseParser
from services.context_service import ContextService
from services.prompt_builder import PromptBuilder
from services.story_engine import StoryEngine

try:
    from services.runtime_visibility_movement_adapter import RuntimeVisibilityMovementAdapter
    from services.runtime_visibility_turn_output import make_turn_output
except Exception:  # pragma: no cover
    RuntimeVisibilityMovementAdapter = None  # type: ignore
    make_turn_output = None  # type: ignore
try:
    from services.runtime_mode_router import RuntimeModeRouter
except Exception:  # pragma: no cover
    RuntimeModeRouter = None  # type: ignore


class GameTurnService:
    def __init__(self, channel_repo, party_repo, context_service: ContextService, prompt_builder: PromptBuilder, llm_adapter, story_engine: StoryEngine, parser: Optional[LLMResponseParser] = None, movement_service=None, rest_service=None, replace_player_placeholder: bool = True, campaign_repo=None, project_root: str = ".", visibility_movement_adapter=None, runtime_mode_service=None, runtime_mode_router=None) -> None:
        self.channel_repo = channel_repo
        self.party_repo = party_repo
        self.context_service = context_service
        self.prompt_builder = prompt_builder
        self.llm_adapter = llm_adapter
        self.story_engine = story_engine
        self.parser = parser or LLMResponseParser()
        self.movement_service = movement_service
        self.rest_service = rest_service
        self.replace_player_placeholder = replace_player_placeholder
        self.campaign_repo = campaign_repo
        self.project_root = project_root
        self.runtime_mode_service = runtime_mode_service
        if visibility_movement_adapter is not None:
            self.visibility_movement_adapter = visibility_movement_adapter
        elif RuntimeVisibilityMovementAdapter is not None:
            self.visibility_movement_adapter = RuntimeVisibilityMovementAdapter(campaign_repo=campaign_repo, project_root=project_root)
        else:
            self.visibility_movement_adapter = None
        if runtime_mode_router is not None:
            self.runtime_mode_router = runtime_mode_router
        elif runtime_mode_service is not None and RuntimeModeRouter is not None:
            self.runtime_mode_router = RuntimeModeRouter(runtime_mode_service=runtime_mode_service, visibility_movement_adapter=self.visibility_movement_adapter)
        else:
            self.runtime_mode_router = None

    def process(self, channel_id: str, player_id: str, text: str, campaign_id_override: Optional[str] = None) -> TurnOutput:
        channel_id = str(channel_id)
        player_id = str(player_id)
        text = str(text or "").strip()
        if not text:
            return TurnOutput(public_narrative="Nem hallatszik érthető akció. Kérlek írd le, mit teszel.")
        self._pre_turn_state_update(channel_id, player_id, text)
        runtime_output = self._try_handle_runtime_mode(channel_id, player_id, text, campaign_id_override=campaign_id_override)
        if runtime_output is not None:
            return self._finalize_output(runtime_output, player_id)
        if self.rest_service:
            rest_output = self.rest_service.try_handle_rest(channel_id, player_id, text)
            if rest_output is not None:
                return self._finalize_output(rest_output, player_id)
        if self.movement_service:
            movement_output = self.movement_service.try_handle_movement(channel_id, text, player_id=player_id)
            if movement_output is not None:
                return self._finalize_output(movement_output, player_id)
        context = self.context_service.get_context(channel_id=channel_id, player_id=player_id, player_message=text)
        prompt = self.prompt_builder.build(context, text)
        raw_response = self.llm_adapter.generate(prompt)
        llm_response = self.parser.parse(raw_response)
        active_players = self.party_repo.get_party_members(channel_id) or [player_id]
        output = self.story_engine.apply(channel_id=channel_id, player_id=player_id, response=llm_response, active_players=active_players)
        return self._finalize_output(output, player_id)

    def _try_handle_runtime_mode(self, channel_id: str, player_id: str, text: str, campaign_id_override: Optional[str] = None) -> Optional[TurnOutput]:
        campaign_id = str(campaign_id_override) if campaign_id_override else self._active_campaign_id(channel_id)
        if not campaign_id:
            return None
        if self.runtime_mode_router is not None:
            routed = self.runtime_mode_router.try_handle_pre_llm(channel_repo=self.channel_repo, channel_id=channel_id, player_id=player_id, campaign_id=campaign_id, text=text)
            if routed.handled and routed.output:
                return self._visibility_result_to_turn_output(routed.output, campaign_id, extra_debug=routed.to_debug())
            return None
        if not self.visibility_movement_adapter:
            return None
        result = self.visibility_movement_adapter.try_handle(channel_id=channel_id, player_id=player_id, campaign_id=campaign_id, text=text)
        if not result or not result.get("handled"):
            return None
        return self._visibility_result_to_turn_output(result, campaign_id)

    def _visibility_result_to_turn_output(self, result, campaign_id: str, extra_debug=None) -> TurnOutput:
        public_text = result.get("text") or "A helyzet változatlan."
        debug = {"visibility_result": result.get("raw"), "campaign_id": campaign_id}
        if extra_debug:
            debug["runtime_route"] = extra_debug
        if make_turn_output is not None:
            return make_turn_output(public_text, debug=debug)
        return TurnOutput(public_narrative=public_text)

    def _active_campaign_id(self, channel_id: str) -> Optional[str]:
        state = None
        for method_name in ("get_state", "get_channel_state", "load_state"):
            method = getattr(self.channel_repo, method_name, None)
            if not method:
                continue
            try:
                state = method(channel_id)
                break
            except Exception:
                continue
        if isinstance(state, dict):
            campaign_id = state.get("campaign_id") or state.get("campaign")
            mode = str(state.get("mode") or "campaign").lower()
            if campaign_id:
                return str(campaign_id)
            if mode == "campaign":
                return "default"
            return None
        return "default"

    def bind_channel_campaign_for_smoke(self, *, channel_id: str, campaign_id: str, mode: str = "dungeon") -> bool:
        """Best-effort helper for smoke/debug scripts using ChannelRepository.save_state()."""
        state = {}
        try:
            state = self.channel_repo.get_state(channel_id) or {}
        except Exception:
            state = {}
        if not isinstance(state, dict):
            state = {}
        state["campaign_id"] = str(campaign_id)
        state["mode"] = str(mode)
        state["runtime_mode"] = str(mode).upper()
        state["bundle_available"] = True
        state["visibility_available"] = mode.lower() in {"dungeon", "hybrid"}
        state["map_available"] = mode.lower() in {"dungeon", "hybrid"}
        save = getattr(self.channel_repo, "save_state", None)
        if save:
            save(str(channel_id), state)
            return True
        return False

    def _pre_turn_state_update(self, channel_id: str, player_id: str, text: str) -> None:
        self.party_repo.add_player(channel_id, player_id)
        self.channel_repo.add_player(channel_id, player_id)
        self.channel_repo.append_context_message(channel_id, player_id, text, limit=10)

    def _finalize_output(self, output: TurnOutput, player_id: str) -> TurnOutput:
        if self.replace_player_placeholder:
            output.avrae_commands = [self._replace_player_placeholder(command, player_id) for command in output.avrae_commands]
        if not output.public_narrative:
            output.public_narrative = "A jelenet feszült csendben folytatódik. Mit tesztek?"
        return output

    @staticmethod
    def _replace_player_placeholder(command: str, player_id: str) -> str:
        return str(command).replace("PLAYER", f"<@{player_id}>")
