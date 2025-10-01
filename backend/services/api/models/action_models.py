from pydantic import BaseModel
from typing import Optional
from enum import Enum
from backend.core.characters.character_models import CharacterType


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


class ParseActionRequest(BaseModel):
    action: str
    actor_type: CharacterType


class GenerateActionRequest(BaseModel):
    parsed_action: ParsedAction
    hit: bool
    damage_type: Optional[str] = "wound"


class GenerateInvalidActionRequest(BaseModel):
    validation_result: ValidationResult
    parsed_action: ParsedAction
