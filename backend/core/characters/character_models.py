from typing import Optional
from pydantic import BaseModel
from enum import Enum


class CharacterType(Enum):
    PLAYER = "player"
    NPC = "npc"


class CreatureType(Enum):
    HUMANOID = "humanoid"
    BEAST = "beast"
    UNDEAD = "undead"
    CONSTRUCT = "construct"
    ELEMENTAL = "elemental"
    DRAGON = "dragon"
    GIANT = "giant"
    CELESTIAL = "celestial"
    FIEND = "fiend"


class ConditionEffect(Enum):
    BLEEDING = "bleeding"  # stackable
    BLINDING = "blinded"
    CHARMED = "charmed"
    DEAFENED = "deafened"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"  # stackable
    PRONE = "prone"
    RESTRAINED = "restrained"
    SILENCED = "silenced"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"
    EXHAUSTION = "exhaustion"  # stackable - Eh? may or may not be used


class Disposition(Enum):
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    AGGRESIVE = "aggresive"


class ConditionEffectInstance(BaseModel):
    """Represents an active status effect on a character"""

    effect: ConditionEffect
    duration: int  # turns remaining, -1 for permanent
    intensity: int = 1  # Bleeding, Poisioned and Exhaustion can stack
    source: Optional[str] = None  # what caused this effect
