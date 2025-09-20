"""
Pydantic models for the D&D narrator system.
Centralized data structures used across all components.
"""

from fastapi import Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field


class CharacterType(Enum):
    player = "player"
    npc = "npc"
    enemy = "enemy"  # Hostile NPC
    ally = "ally"


class StatusEffect(Enum):
    poisoned = "poisoned"
    paralyzed = "paralyzed"
    stunned = "stunned"
    blessed = "blessed"
    cursed = "cursed"
    invisible = "invisible"
    haste = "haste"
    slow = "slow"
    charmed = "charmed"
    frightened = "frightened"
    prone = "prone"
    grappled = "grappled"
    restrained = "restrained"
    incapaciatated = "incapacitated"
    unconscious = "unconscious"


class GameCondition(Enum):
    game_on = "game_on"
    player_win = "player_win"
    player_defeat = "player_defeat"
    game_over = "game_over"


class ActionType(str, Enum):
    attack = "attack"
    spell = "spell"
    social = "social"
    movement = "movement"
    interact = "interact"


class DamageType(str, Enum):
    miss = "miss"
    failure = "failure"
    wound = "wound"
    critical = "critical"
    kill = "kill"
    success = "success"
    great_success = "great_success"
    outstanding_success = "outstanding_success"


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
    actor_type: CharacterType
    action: str
    target: Optional[str] = None
    action_type: ActionType
    weapon: Optional[str] = None
    subject: Optional[str] = None
    details: Optional[str] = None


class ActionResult(BaseModel):
    parsed_action: ParsedAction
    action_type: ActionType
    hit: bool
    dice_roll: int
    damage_type: DamageType
    narration: str
    difficulty: Optional[int] = None


class ValidationResult(BaseModel):
    is_valid: bool
    reason: Optional[str] = None
    suggested_action: Optional[str] = None


class GameContext(BaseModel):
    scene_description: Optional[str] = None
    active_characters: List[str] = []
    environment: Optional[str] = None
    difficulty_modifier: int = 0


# -------------------------
# Scene and Exit structures
# -------------------------


class Exit:
    id: str
    label: str
    target_scene: str
    is_locked: Optional[bool] = None
    zone: Optional[str] = None


class Scene:
    id: str
    title: str
    description: str
    exits: list[Exit] = field(default_factory=list)
    objects: dict = field(default_factory=dict)


class SceneDiff:
    scene_id: str
    changes: dict = field(default_factory=dict)


class Structure:
    id: str
    name: str
    description: str


class Status:
    is_alive: bool = True
    is_hostile: bool = False
    health: int = 10


class Disposition(Enum):
    friendly = "friendly"
    neutral = "neutral"
    aggresive = "aggresive"


class NotableNPC:
    id: str
    name: str
    description: str
    status: Status
    disposition: Disposition


class NPC:
    id: str
    name: str
    description: str
    status: Status
    disposition: Disposition


class Item:
    id: str
    name: str
    description: str
    is_interactable: bool = False
    is_loot: bool = False


class Discovery:
    id: str
    type: str
    observation: str
    is_interactable: bool = False
    is_discovered: bool = False
    perception_dc: int
    implication: Optional[str]
    quest: Optional[str]


# -------------------------
# API models
# -------------------------


class ParseActionRequest(BaseModel):
    action: str
    actor_type: CharacterType


class GenerateActionRequest(BaseModel):
    parsed_action: ParsedAction
    hit: bool
    damage_type: Optional[str] = "wound"


class GenerateSceneRequest(BaseModel):
    scene: Dict[str, Any]
    player: Dict[str, Any]


class GeneratedNarration(BaseModel):
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


class GameSessionResponse(BaseModel):
    session_id: str
    engine_id: str
    game_state: Dict[str, Any]
