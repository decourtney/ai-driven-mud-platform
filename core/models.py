"""
Pydantic models for the D&D narrator system.
Centralized data structures used across all components.
"""

from pydantic import BaseModel
from typing import Optional
from enum import Enum


class CharacterType(Enum):
    PLAYER = "player"
    NPC = "npc"
    ENEMY = "enemy"
    ALLY = "ally"


class StatusEffect(Enum):
    POISONED = "poisoned"
    PARALYZED = "paralyzed"
    STUNNED = "stunned"
    BLESSED = "blessed"
    CURSED = "cursed"
    INVISIBLE = "invisible"
    HASTE = "haste"
    SLOW = "slow"
    CHARMED = "charmed"
    FRIGHTENED = "frightened"
    PRONE = "prone"
    GRAPPLED = "grappled"
    RESTRAINED = "restrained"
    INCAPACITATED = "incapacitated"
    UNCONSCIOUS = "unconscious"
    

class GameCondition(Enum):
    CONTINUE = "continue"
    PLAYER_WIN = "player_win"
    PLAYER_DEFEAT = "player_defeat"
    GAME_OVER = "game_over"
    

class ActionType(str, Enum):
    ATTACK = "attack"
    SPELL = "spell"
    SKILL_CHECK = "skill_check"
    SOCIAL = "social"
    MOVEMENT = "movement"
    INTERACT = "interact"


class DamageType(str, Enum):
    MISS = "miss"
    FAILURE = "failure"
    WOUND = "wound"
    CRITICAL = "critical"
    KILL = "kill"
    SUCCESS = "success"
    GREAT_SUCCESS = "great_success"
    OUTSTANDING_SUCCESS = "outstanding_success"


class ParsedAction(BaseModel):
    """Structured representation of a parsed action"""
    actor: str
    action: str
    target: Optional[str] = None
    action_type: ActionType
    weapon: Optional[str] = None
    subject: Optional[str] = None
    details: Optional[str] = None
    parsing_method: Optional[str] = None


class ActionResult(BaseModel):
    """Result of processing an action through the game engine"""
    parsed_action: ParsedAction
    hit: bool
    dice_roll: int
    damage_type: DamageType
    narration: str
    difficulty: Optional[int] = None


class GameContext(BaseModel):
    """Context information for the game session"""
    scene_description: Optional[str] = None
    active_characters: list[str] = []
    environment: Optional[str] = None
    difficulty_modifier: int = 0


# API Request/Response models
class ProcessUserInputRequest(BaseModel):
    user_input: str


class StructuredActionRequest(BaseModel):
    parsed_action: ParsedAction
    hit: bool
    damage_type: Optional[str] = "wound"
    context: Optional[GameContext] = None


class HealthResponse(BaseModel):
    status: str
    components: dict[str, bool]  # component_name: is_loaded