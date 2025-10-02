from enum import Enum

class GameCondition(Enum):
    game_on = "game_on"
    player_win = "player_win"
    player_defeat = "player_defeat"
    game_over = "game_over"


class TurnPhase(Enum):
    scene_narration = "scene_narration"
    player_turn = "player_turn"
    npc_turn = "npc_turn"
    end_turn = "end_turn"









