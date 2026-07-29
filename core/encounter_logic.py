"""
ENCOUNTER_LOGIC.PY - A helyszíni véletlenszerű szörnytáblázatok kiértékeléséért felelős modul.
"""

import re
import random
from typing import Tuple, Optional, Dict, List


def roll_dice_string(dice_str: str) -> int:
    """
    Kiszámolja a standard D&D kockadobásokat string alapján.
    Példa: "1d4" -> visszaad egy számot 1 és 4 között. "1" -> visszaad 1-et.
    """
    if not dice_str or dice_str.isdigit():
        return int(dice_str) if dice_str.isdigit() else 1
        
    match = re.match(r'(\d+)d(\d+)', dice_str.lower())
    if match:
        count = int(match.group(1))
        sides = int(match.group(2))
        return sum(random.randint(1, sides) for _ in range(count))
    return 1


def roll_from_encounter_table(encounter_table: Dict[str, List[str]]) -> Optional[Tuple[int, str]]:
    """
    Dob egy d20-at, és a szoba táblázata alapján kiválasztja a szörnyet és a darabszámot.
    Visszatérési érték: (darabszám, "Szörny Neve") vagy None
    """
    if not encounter_table:
        return None
        
    d20_roll = random.randint(1, 20)
    
    for dice_range, monster_info in encounter_table.items():
        # Szétbontjuk a tartományt (pl. "11-15" -> min: 11, max: 15)
        if "-" in dice_range:
            min_val, max_val = map(int, dice_range.split("-"))
        else:
            min_val = max_val = int(dice_range)
            
        if min_val <= d20_roll <= max_val:
            dice_count_str = monster_info[0] # Pl. "1d4"
            monster_name = monster_info[1]    # Pl. "Giant Rat"
            
            actual_count = roll_dice_string(dice_count_str)
            return actual_count, monster_name
            
    return None
