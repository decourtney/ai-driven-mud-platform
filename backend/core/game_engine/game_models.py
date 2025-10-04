from enum import Enum


class GameCondition(Enum):
    GAME_ON = "GAME_ON"
    PLAYER_WIN = "PLAYER_WIN"
    PLAYER_DEFEAT = "PLAYER_DEFEAT"
    GAME_OVER = "GAME_OVER"


class TurnPhase(Enum):
    SCENE_NARRATION = "SCENE_NARRATION"
    PLAYER_TURN = "PLAYER_TURN"
    NPC_TURN = "NPC_TURN"
    END_TURN = "END_TURN"
