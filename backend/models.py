"""
Pydantic models for the D&D narrator system.
Centralized data structures used across all components.
"""

from fastapi import Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum


class ValidationResult:
    """Result of action validation"""

    def __init__(
        self,
        is_valid: bool,
        reason: Optional[str] = None,
        suggested_action: Optional[str] = None,
    ):
        self.is_valid = is_valid
        self.reason = reason
        self.suggested_action = suggested_action


class CharacterType(Enum):
    PLAYER = "player"
    NPC = "npc"
    ENEMY = "enemy"  # Hostile NPC
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


class GameStatus(str, Enum):
    active = "active"
    maintenance = "maintenance"
    beta = "beta"


class GameDifficulty(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class ParsedAction(BaseModel):
    actor: str
    action: str
    target: Optional[str] = None
    action_type: ActionType
    weapon: Optional[str] = None
    subject: Optional[str] = None
    details: Optional[str] = None


class ActionResult(BaseModel):
    parsed_action: ParsedAction
    hit: bool
    dice_roll: int
    damage_type: DamageType
    narration: str
    difficulty: Optional[int] = None


class GameContext(BaseModel):
    """Context information for the game session"""

    scene_description: Optional[str] = None
    active_characters: List[str] = []
    environment: Optional[str] = None
    difficulty_modifier: int = 0


# API models
class ParseActionRequest(BaseModel):
    action: str


class ParseActionResponse(BaseModel):
    actor: str
    action: str
    target: Optional[str] = None
    action_type: ActionType
    weapon: Optional[str] = None
    subject: Optional[str] = None
    details: Optional[str] = None


class GenerateActionRequest(BaseModel):
    parsed_action: ParsedAction
    hit: bool
    damage_type: Optional[str] = "wound"


class GenerateSceneRequest(BaseModel):
    scene: Dict[str, Any]
    player: Dict[str, Any]
    npcs: List[Dict[str, Any]]


class GenerateNarrationResponse(BaseModel):
    # Reponse for any narration generation
    narration: str


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    parser_ready: bool
    narrator_ready: bool
    memory_usage: Dict[str, Any]
    uptime_seconds: float


class GameInfo(BaseModel):
    slug: str
    engine: str
    title: str
    description: str
    player_count: int
    status: GameStatus
    difficulty: GameDifficulty
    estimated_time: str
    features: List[str]
    thumbnail: str
    tags: List[str]


class GameSessionCreate(BaseModel):
    user_id: str
    slug: str
    player_state: Dict[str, Any]


class GameSessionGet(BaseModel):
    user_id: str
    slug: str
    session_id: str


class GameSessionDelete(BaseModel):
    user_id: str = Query(...)
    slug: str
    session_id: str


class GameSessionResponse(BaseModel):
    session_id: str
    user_id: str
    slug: str
    game_state: Dict[str, Any]
