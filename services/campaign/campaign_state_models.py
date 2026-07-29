from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

class QuestStatus(str, Enum):
    DISCOVERED='discovered'
    ACTIVE='active'
    COMPLETED='completed'
    FAILED='failed'

@dataclass
class LocationState:
    location_id:str
    name:str
    discovered:bool=False
    visited:bool=False
    tags:List[str]=field(default_factory=list)

@dataclass
class NpcState:
    npc_id:str
    name:str
    goal:str=''
    fear:str=''
    secret:str=''
    relationship_to_party:int=0
    known_information:List[str]=field(default_factory=list)

@dataclass
class FactionState:
    faction_id:str
    name:str
    reputation:int=0
    objectives:List[str]=field(default_factory=list)

@dataclass
class QuestState:
    quest_id:str
    title:str
    status:QuestStatus=QuestStatus.DISCOVERED
    known_clues:List[str]=field(default_factory=list)
    next_leads:List[str]=field(default_factory=list)

@dataclass
class PartyKnowledgeState:
    known_locations:List[str]=field(default_factory=list)
    known_npcs:List[str]=field(default_factory=list)
    known_clues:List[str]=field(default_factory=list)

@dataclass
class CampaignWorldTruth:
    truth_id:str
    summary:str
    revealed:bool=False

@dataclass
class CampaignState:
    campaign_id:str
    title:str
    theme:str=''
    tone:str=''
    active_location_id:str=''
    locations:Dict[str, LocationState]=field(default_factory=dict)
    npcs:Dict[str, NpcState]=field(default_factory=dict)
    factions:Dict[str, FactionState]=field(default_factory=dict)
    quests:Dict[str, QuestState]=field(default_factory=dict)
    knowledge:PartyKnowledgeState=field(default_factory=PartyKnowledgeState)
    world_truths:List[CampaignWorldTruth]=field(default_factory=list)

@dataclass
class CampaignSnapshot:
    snapshot_id:str
    campaign_id:str
    state:CampaignState
