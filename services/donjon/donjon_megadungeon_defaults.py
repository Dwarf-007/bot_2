
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List
@dataclass(frozen=True)
class DonjonLevelSettings:
    dungeon_size: str='Medium'; dungeon_layout: str='Rectangle'; peripheral_egress: str='No'; room_layout: str='Scattered'; room_size: str='Medium'; polymorph_rooms: str='Many'; doors: str='Standard'; corridors: str='Labyrinth'; remove_deadends: str='Some'; stairs: str='Yes'; map_style: str='Standard'; grid: str='Square'; motif: str='Undead'; party_size: str='4'
    def to_form_labels(self)->Dict[str,str]: return {'Dungeon Size':self.dungeon_size,'Dungeon Layout':self.dungeon_layout,'Peripheral Egress':self.peripheral_egress,'Room Layout':self.room_layout,'Room Size':self.room_size,'Polymorph Rooms':self.polymorph_rooms,'Doors':self.doors,'Corridors':self.corridors,'Remove Deadends':self.remove_deadends,'Stairs':self.stairs,'Map Style':self.map_style,'Grid':self.grid,'Motif':self.motif,'Party Size':self.party_size}
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class DonjonMegaDungeonPlan:
    level_start:int=1; level_end:int=20; default_direction:str='down'; settings:DonjonLevelSettings=DonjonLevelSettings()
    def levels(self)->List[int]: return list(range(int(self.level_start), int(self.level_end)+1))
    def entry_anchor_for_level(self, level:int)->str: return 'stairs_down_or_entrance' if level<=self.level_start else 'stairs_up_from_previous_level'
    def exit_anchor_for_level(self, level:int)->str: return 'final_objective_or_stairs_up' if level>=self.level_end else 'stairs_down_to_next_level'
    def to_dict(self): return {'level_start':self.level_start,'level_end':self.level_end,'default_direction':self.default_direction,'settings':self.settings.to_dict()}

