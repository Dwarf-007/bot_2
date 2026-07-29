"""
APP/BOOTSTRAP.PY
Dependency wiring for the AI DM engine, including runtime health diagnostics.

Sprint 11.1 update:
- Wires RuntimeModeRouter into RuntimeContainer and GameTurnService.
- Integrates DMCombatService, CampaignManager, PlayerManager for dungeon campaigns.

C3.3 update:
- Removes AvraeClient/AvraeDispatcher from canonical runtime wiring.
- Keeps AvraeParserService + CombatFeedbackService as optional inbound feedback
  processing only.
- Outgoing Avrae commands must be produced as TurnOutput suggestions, not
  dispatched automatically.
"""

from __future__ import annotations
from dataclasses import dataclass

from avrae.avrae_parser import AvraeParserService
from config import AppConfig, load_config
from core.game_events import EventBus, EventTypes
from llm.gemini_client import GeminiClientService
from llm.key_manager import GeminiKeyManager
from llm.llm_response_parser import LLMResponseParser
from llm.ollama_adapter import OllamaAdapter
from llm.provider_router import ProviderRouter
from persistence import database as db
from repositories import ChannelRepository, InventoryRepository, LocationRepository, PartyRepository, PlayerRepository
from repositories.campaign_repository import CampaignRepository
from repositories.campaign_progress_repository import CampaignProgressRepository
from repositories.combat_repository import CombatRepository
from repositories.memory_repository import MemoryRepository
from repositories.rag_chunk_repository import RagChunkRepository
from repositories.room_alias_repository import RoomAliasRepository
from services.admin_debug_service import AdminDebugService
from services.campaign_manager import CampaignManager
from services.campaign_service import CampaignService
from services.combat_feedback_service import CombatFeedbackService
from services.context_service import ContextService
from services.bestiary_service import BestiaryService
from services.dm_combat_service import DMCombatService
from services.encounter_service import EncounterService
from services.game_turn_service import GameTurnService
from services.memory_event_service import MemoryEventService
from services.memory_summary_service import MemorySummaryService
from services.movement_service import MovementService
from services.player_manager import PlayerManager
from services.progress_service import ProgressService
from services.prompt_builder import PromptBuilder
from services.rag_runtime import ExistingSchemaRagRuntime
from services.rest_service import RestService
from services.room_alias_service import RoomAliasService
from services.runtime_health_service import RuntimeHealthService
from services.runtime_mode_router import RuntimeModeRouter
from services.runtime_mode_service import RuntimeModeService
from services.runtime_visibility_command_handler import RuntimeVisibilityCommandHandler
from services.runtime_visibility_movement_adapter import RuntimeVisibilityMovementAdapter
from services.runtime_visibility_state_service import RuntimeVisibilityStateService
from services.story_engine import StoryEngine
from services.trap_resolution_service import TrapResolutionService
from services.visibility_runtime_formatter import VisibilityRuntimeFormatter
from subscribers.memory_logging_subscriber import MemoryLoggingSubscriber


@dataclass
class RuntimeContainer:
    # --- Eventing / health / runtime modes ---
    event_bus: EventBus
    runtime_health_service: RuntimeHealthService
    runtime_mode_service: RuntimeModeService
    runtime_mode_router: RuntimeModeRouter
    runtime_visibility_state_service: RuntimeVisibilityStateService
    runtime_visibility_command_handler: RuntimeVisibilityCommandHandler
    runtime_visibility_adapter: RuntimeVisibilityMovementAdapter

    # --- Persistence / repositories ---
    campaign_repo: CampaignRepository
    progress_repo: CampaignProgressRepository
    room_alias_repo: RoomAliasRepository
    channel_repo: ChannelRepository
    party_repo: PartyRepository
    player_repo: PlayerRepository
    inventory_repo: InventoryRepository
    location_repo: LocationRepository
    combat_repo: CombatRepository
    memory_repo: MemoryRepository
    rag_chunk_repo: RagChunkRepository

    # --- Campaign / RAG / memory services ---
    campaign_service: CampaignService
    progress_service: ProgressService
    room_alias_service: RoomAliasService
    rag_runtime: ExistingSchemaRagRuntime
    memory_event_service: MemoryEventService
    memory_summary_service: MemorySummaryService
    context_service: ContextService
    admin_debug_service: AdminDebugService

    # --- Dungeon campaign services ---
    dm_combat_service: DMCombatService
    campaign_manager: CampaignManager
    player_manager: PlayerManager

    # --- LLM / story / turn orchestration ---
    prompt_builder: PromptBuilder
    llm_adapter: ProviderRouter
    trap_resolution_service: TrapResolutionService
    movement_service: MovementService
    rest_service: RestService
    encounter_service: EncounterService
    story_engine: StoryEngine
    game_turn_service: GameTurnService

    # Optional inbound Avrae feedback parser/processor. Not used for outgoing dispatch.
    combat_feedback_service: CombatFeedbackService


def build_runtime(rag_runtime=None, config: AppConfig | None = None) -> RuntimeContainer:
    config = config or load_config(require_discord_token=False)
    db.initialize_database()
    event_bus = EventBus()

    # ------------------------------------------------------------------
    # 1. Repository réteg
    # ------------------------------------------------------------------
    campaign_repo = CampaignRepository(db); campaign_repo.ensure_schema()
    progress_repo = CampaignProgressRepository(db); progress_repo.ensure_schema()
    channel_repo = ChannelRepository(db)
    party_repo = PartyRepository(db)
    player_repo = PlayerRepository(db)
    inventory_repo = InventoryRepository(db)
    location_repo = LocationRepository(db)
    combat_repo = CombatRepository(db); combat_repo.ensure_schema()
    memory_repo = MemoryRepository(db); memory_repo.ensure_schema()
    rag_chunk_repo = RagChunkRepository(db); rag_chunk_repo.ensure_schema()
    room_alias_repo = RoomAliasRepository(db); room_alias_repo.ensure_schema()

    # ------------------------------------------------------------------
    # 2. Alap kampány és RAG szolgáltatások
    # ------------------------------------------------------------------
    room_alias_service = RoomAliasService(room_alias_repo, location_repo=location_repo)
    active_rag_runtime = rag_runtime or ExistingSchemaRagRuntime(rag_chunk_repo)
    campaign_service = CampaignService(
        campaign_repo=campaign_repo, channel_repo=channel_repo,
        location_repo=location_repo, rag_chunk_repo=rag_chunk_repo, memory_repo=memory_repo
    )
    campaign_service.ensure_campaign("default", name="Default Campaign")
    progress_service = ProgressService(
        progress_repo, channel_repo, campaign_service=campaign_service, location_repo=location_repo
    )

    # ------------------------------------------------------------------
    # 3. LLM adapter
    # ------------------------------------------------------------------
    llm_adapter = build_llm_router(config)

    # ------------------------------------------------------------------
    # 4. Dungeon szolgáltatások
    # ------------------------------------------------------------------
    # C3.3 boundary:
    # No AvraeClient/AvraeDispatcher is created in the canonical runtime.
    # Any Avrae commands must be emitted as TurnOutput suggestions for the DM.
    bestiary_service = BestiaryService(
        path=getattr(config, 'bestiary_path', None) or "data/bestiary.json",
    )
    dm_combat_service = DMCombatService(
        llm_adapter=llm_adapter,
        bestiary_service=bestiary_service,
        avrae_dispatcher=None,
        player_manager=None,  # később beállítható
    )

    # Optional inbound Avrae feedback processing. This is not outgoing dispatch.
    combat_feedback_service = CombatFeedbackService(
        combat_repo=combat_repo,
        event_bus=event_bus,
        parser=AvraeParserService(),
        dm_combat_service=dm_combat_service,
    )

    campaign_manager = CampaignManager(
        channel_repo=channel_repo,
        campaign_repo=campaign_repo,
        combat_service=dm_combat_service,
        campaign_data_dir=getattr(config, 'campaign_data_dir', None) or "campaigns",
    )

    player_manager = PlayerManager(channel_repo=channel_repo)

    # ------------------------------------------------------------------
    # 5. Runtime mód szolgáltatások
    # ------------------------------------------------------------------
    runtime_mode_service = RuntimeModeService(project_root=".", campaign_repo=campaign_repo)
    runtime_visibility_state_service = RuntimeVisibilityStateService(
        enable_legacy_last_fallback=False, write_legacy_last=True
    )
    visibility_formatter = VisibilityRuntimeFormatter()
    runtime_visibility_command_handler = RuntimeVisibilityCommandHandler(
        state_service=runtime_visibility_state_service, formatter=visibility_formatter
    )
    runtime_visibility_adapter = RuntimeVisibilityMovementAdapter(
        campaign_repo=campaign_repo, project_root="."
    )
    runtime_visibility_adapter.state_service = runtime_visibility_state_service
    runtime_visibility_adapter.formatter = visibility_formatter
    runtime_visibility_adapter.command_handler = runtime_visibility_command_handler
    runtime_mode_router = RuntimeModeRouter(
        runtime_mode_service=runtime_mode_service,
        visibility_movement_adapter=runtime_visibility_adapter,
        allow_unknown_dungeon_probe=True,
    )

    # ------------------------------------------------------------------
    # 6. Health és memory szolgáltatások
    # ------------------------------------------------------------------
    runtime_health_service = RuntimeHealthService(
        config=config, campaign_repo=campaign_repo, channel_repo=channel_repo,
        location_repo=location_repo, rag_chunk_repo=rag_chunk_repo,
        room_alias_repo=room_alias_repo, progress_repo=progress_repo,
        memory_repo=memory_repo, llm_adapter=llm_adapter
    )

    memory_event_service = MemoryEventService(memory_repo)
    memory_summary_service = MemorySummaryService()
    memory_subscriber = MemoryLoggingSubscriber(memory_event_service)
    for event_type in memory_event_service.persisted_event_types:
        event_bus.register(event_type, memory_subscriber.handle)

    # Wire player roll feedback into DM combat state.
    # This remains local/in-process and does not imply Avrae command dispatch.
    event_bus.register(EventTypes.PLAYER_ROLL, dm_combat_service.on_player_roll)

    # ------------------------------------------------------------------
    # 7. Játékmenet szolgáltatások
    # ------------------------------------------------------------------
    encounter_service = EncounterService(combat_feedback_service=combat_feedback_service)
    trap_resolution_service = TrapResolutionService(
        channel_repo=channel_repo, location_repo=location_repo, event_bus=event_bus
    )
    movement_service = MovementService(
        channel_repo=channel_repo, location_repo=location_repo, event_bus=event_bus,
        trap_resolution_service=trap_resolution_service, room_alias_service=room_alias_service
    )
    rest_service = RestService(
        channel_repo=channel_repo, location_repo=location_repo, event_bus=event_bus,
        encounter_service=encounter_service
    )
    context_service = ContextService(
        channel_repo=channel_repo, location_repo=location_repo,
        rag_runtime=active_rag_runtime, memory_repo=memory_repo,
        memory_summary_service=memory_summary_service, progress_service=progress_service
    )
    prompt_builder = PromptBuilder()
    story_engine = StoryEngine(
        channel_repo=channel_repo, inventory_repo=inventory_repo, player_repo=player_repo,
        location_repo=location_repo, event_bus=event_bus,
        encounter_service=encounter_service, movement_service=movement_service
    )

    # ------------------------------------------------------------------
    # 8. GameTurnService
    # ------------------------------------------------------------------
    game_turn_service = GameTurnService(
        channel_repo=channel_repo,
        party_repo=party_repo,
        context_service=context_service,
        prompt_builder=prompt_builder,
        llm_adapter=llm_adapter,
        story_engine=story_engine,
        parser=LLMResponseParser(),
        movement_service=movement_service,
        rest_service=rest_service,
        campaign_repo=campaign_repo,
        project_root=".",
        visibility_movement_adapter=runtime_visibility_adapter,
        runtime_mode_service=runtime_mode_service,
        runtime_mode_router=runtime_mode_router,
        campaign_manager=campaign_manager,
        player_manager=player_manager,
    )

    # ------------------------------------------------------------------
    # 9. Admin debug szolgáltatás
    # ------------------------------------------------------------------
    admin_debug_service = AdminDebugService(
        channel_repo=channel_repo, party_repo=party_repo, player_repo=player_repo,
        inventory_repo=inventory_repo, location_repo=location_repo, memory_repo=memory_repo,
        memory_summary_service=memory_summary_service, combat_repo=combat_repo,
        rag_runtime=active_rag_runtime, campaign_service=campaign_service,
        room_alias_service=room_alias_service, progress_service=progress_service,
        runtime_health_service=runtime_health_service
    )

    # ------------------------------------------------------------------
    # 10. RuntimeContainer összeállítása
    # ------------------------------------------------------------------
    return RuntimeContainer(
        event_bus=event_bus,
        runtime_health_service=runtime_health_service,
        runtime_mode_service=runtime_mode_service,
        runtime_mode_router=runtime_mode_router,
        runtime_visibility_state_service=runtime_visibility_state_service,
        runtime_visibility_command_handler=runtime_visibility_command_handler,
        runtime_visibility_adapter=runtime_visibility_adapter,
        campaign_repo=campaign_repo,
        progress_repo=progress_repo,
        room_alias_repo=room_alias_repo,
        channel_repo=channel_repo,
        party_repo=party_repo,
        player_repo=player_repo,
        inventory_repo=inventory_repo,
        location_repo=location_repo,
        combat_repo=combat_repo,
        memory_repo=memory_repo,
        rag_chunk_repo=rag_chunk_repo,
        campaign_service=campaign_service,
        progress_service=progress_service,
        room_alias_service=room_alias_service,
        rag_runtime=active_rag_runtime,
        memory_event_service=memory_event_service,
        memory_summary_service=memory_summary_service,
        context_service=context_service,
        admin_debug_service=admin_debug_service,
        dm_combat_service=dm_combat_service,
        campaign_manager=campaign_manager,
        player_manager=player_manager,
        prompt_builder=prompt_builder,
        llm_adapter=llm_adapter,
        trap_resolution_service=trap_resolution_service,
        movement_service=movement_service,
        rest_service=rest_service,
        encounter_service=encounter_service,
        story_engine=story_engine,
        game_turn_service=game_turn_service,
        combat_feedback_service=combat_feedback_service,
    )


def build_llm_router(config: AppConfig) -> ProviderRouter:
    providers = [
        GeminiClientService(
            key_manager=GeminiKeyManager(
                config.gemini_api_keys, cooldown_seconds=config.gemini_key_cooldown_seconds
            ),
            model=config.gemini_model,
            max_total_attempts=config.gemini_max_total_attempts,
            key_cooldown_seconds=config.gemini_key_cooldown_seconds,
        )
    ]
    if config.llm_enable_ollama_fallback:
        providers.append(
            OllamaAdapter(base_url=config.ollama_base_url, model=config.ollama_model)
        )
    return ProviderRouter(providers)


def register_discord_subscribers(runtime: RuntimeContainer, bot) -> None:
    from services.async_event_bridge import AsyncEventBridge
    from subscribers.combat_resolution_subscriber import CombatResolutionSubscriber
    bridge = AsyncEventBridge()
    combat_subscriber = CombatResolutionSubscriber(bot, runtime.party_repo, runtime.player_repo)
    runtime.event_bus.register(
        EventTypes.ALL_MONSTERS_DEFEATED, bridge.wrap(combat_subscriber.on_all_monsters_defeated_async)
    )
