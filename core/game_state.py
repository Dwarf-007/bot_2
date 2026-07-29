
from enum import Enum

class GameState(str, Enum):
    EXPLORATION = "EXPLORATION"
    COMBAT = "COMBAT"
    REST = "REST"
