"""
SERVICES/COMPENDIUM
Foundation package for advisory/reference compendium integration.
"""

from services.compendium.character_creation_advisor import (
    CharacterBuildRole,
    CharacterCreationAdvice,
    CharacterCreationAdvisor,
    CharacterCreationChecklistItem,
    CharacterCreationLookupSummary,
    CharacterCreationRequest,
)
from services.compendium.character_creation_application_service import (
    CharacterCreationApplicationRequest,
    CharacterCreationApplicationService,
    CharacterCreationTurnOutputMapper,
)
from services.compendium.character_option_service import (
    CharacterOptionMatch,
    CharacterOptionResult,
    CharacterOptionService,
    ClassLevelFeature,
    ClassLevelFeatureResult,
)
from services.compendium.compendium_index_service import CompendiumIndexService, CompendiumIndexStats
from services.compendium.compendium_models import (
    CompendiumEntry,
    CompendiumEntryType,
    CompendiumQuery,
    CompendiumSearchResult,
)
from services.compendium.fiveetools_data_source import FiveEToolsDataSource
from services.compendium.level_up_advisor import LevelUpAdvice, LevelUpAdvisor, LevelUpChecklistItem
from services.compendium.rules_reference_service import (
    RulesReferenceMatch,
    RulesReferenceResult,
    RulesReferenceService,
)
from services.compendium.source_policy import SourcePolicy
from services.compendium.spell_reference_service import (
    SpellReferenceMatch,
    SpellReferenceResult,
    SpellReferenceService,
)
from services.compendium.module_reference_service import (
    ModuleContentNode,
    ModuleReferenceMatch,
    ModuleReferenceQuery,
    ModuleReferenceResult,
    ModuleReferenceService,
)
from services.compendium.module_reference_application_service import (
    ModuleReferenceApplicationRequest,
    ModuleReferenceApplicationResult,
    ModuleReferenceApplicationService,
    ModuleReferenceTurnOutputMapper,
)
from services.compendium.campaign_content_advisor import (
    CampaignContentAdvice,
    CampaignContentAdvisor,
    CampaignContentHint,
    CampaignContentKind,
)
from services.compendium.campaign_content_application_service import (
    CampaignContentApplicationRequest,
    CampaignContentApplicationResult,
    CampaignContentApplicationService,
    CampaignContentTurnOutputMapper,
)
from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionApprovalStatus,
    CampaignStateTransitionEvidence,
    CampaignStateTransitionProposal,
    CampaignStateTransitionProposalResult,
    CampaignStateTransitionRisk,
    CampaignStateTransitionSource,
    CampaignStateTransitionType,
    build_proposal_id,
    proposal_requires_approval,
)
from services.compendium.campaign_state_transition_proposal_service import (
    CampaignStateTransitionProposalRequest,
    CampaignStateTransitionProposalService,
)
from services.compendium.campaign_transition_approval_policy import (
    CampaignTransitionApprovalBatchDecision,
    CampaignTransitionApprovalCategory,
    CampaignTransitionApprovalDecision,
    CampaignTransitionApprovalPolicy,
)
from services.compendium.campaign_state_transition_application_service import (
    CampaignStateTransitionApplicationRequest,
    CampaignStateTransitionApplicationResult,
    CampaignStateTransitionApplicationService,
    CampaignStateTransitionTurnOutputMapper,
)
from services.compendium.campaign_state_transition_aggregate_gate import (
    CampaignStateTransitionAggregateCheck,
    CampaignStateTransitionAggregateGate,
    CampaignStateTransitionAggregateResult,
) 

__all__ = [
    "CompendiumEntry",
    "CompendiumEntryType",
    "CompendiumQuery",
    "CompendiumSearchResult",
    "CompendiumIndexService",
    "CompendiumIndexStats",
    "FiveEToolsDataSource",
    "RulesReferenceMatch",
    "RulesReferenceResult",
    "RulesReferenceService",
    "SpellReferenceMatch",
    "SpellReferenceResult",
    "SpellReferenceService",
    "CharacterOptionMatch",
    "CharacterOptionResult",
    "CharacterOptionService",
    "ClassLevelFeature",
    "ClassLevelFeatureResult",
    "LevelUpAdvice",
    "LevelUpAdvisor",
    "LevelUpChecklistItem",
    "CharacterBuildRole",
    "CharacterCreationAdvice",
    "CharacterCreationAdvisor",
    "CharacterCreationChecklistItem",
    "CharacterCreationLookupSummary",
    "CharacterCreationRequest",
    "CharacterCreationApplicationRequest",
    "CharacterCreationApplicationService",
    "CharacterCreationTurnOutputMapper",
    "SourcePolicy",
    "ModuleContentNode",
    "ModuleReferenceMatch",
    "ModuleReferenceQuery",
    "ModuleReferenceResult",
    "ModuleReferenceService",
    "ModuleReferenceApplicationRequest",
    "ModuleReferenceApplicationResult",
    "ModuleReferenceApplicationService",
    "ModuleReferenceTurnOutputMapper",
    "CampaignContentAdvice",
    "CampaignContentAdvisor",
    "CampaignContentHint",
    "CampaignContentKind",
    "CampaignContentApplicationRequest",
    "CampaignContentApplicationResult",
    "CampaignContentApplicationService",
    "CampaignContentTurnOutputMapper",
    "CampaignStateTransitionApprovalStatus",
    "CampaignStateTransitionEvidence",
    "CampaignStateTransitionProposal",
    "CampaignStateTransitionProposalResult",
    "CampaignStateTransitionRisk",
    "CampaignStateTransitionSource",
    "CampaignStateTransitionType",
    "build_proposal_id",
    "proposal_requires_approval",
    "CampaignStateTransitionProposalRequest",
    "CampaignStateTransitionProposalService",
    "CampaignTransitionApprovalBatchDecision",
    "CampaignTransitionApprovalCategory",
    "CampaignTransitionApprovalDecision",
    "CampaignTransitionApprovalPolicy",
    "CampaignStateTransitionApplicationRequest",
    "CampaignStateTransitionApplicationResult",
    "CampaignStateTransitionApplicationService",
    "CampaignStateTransitionTurnOutputMapper",
    "CampaignStateTransitionAggregateCheck",
    "CampaignStateTransitionAggregateGate",
    "CampaignStateTransitionAggregateResult",
]
