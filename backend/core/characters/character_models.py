from typing import Optional
from pydantic import BaseModel
from enum import Enum


class CharacterType(Enum):
    PLAYER = "PLAYER"
    NPC = "NPC"


class CreatureType(Enum):
    ABERRATION = "ABERRATION"
    BEAST = "BEAST"
    CELESTIAL = "CELESTIAL"
    CONSTRUCT = "CONSTRUCT"
    DRAGON = "DRAGON"
    ELEMENTAL = "ELEMENTAL"
    FEY = "FEY"
    FIEND = "FIEND"
    GIANT = "GIANT"
    HUMANOID = "HUMANOID"
    MONSTROSITY = "MONSTROSITY"
    OOZE = "OOZE"
    PLANT = "PLANT"
    UNDEAD = "UNDEAD"


class ConditionEffect(Enum):
    BLEEDING = "BLEEDING"  # stackable
    BLINDING = "BLINDED"
    CHARMED = "CHARMED"
    DEAFENED = "deafened"
    FRIGHTENED = "FRIGHTENED"
    GRAPPLED = "GRAPPLED"
    INCAPACITATED = "INCAPACITATED"
    INVISIBLE = "INVISIBLE"
    PARALYZED = "PARALYZED"
    PETRIFIED = "PETRIFIED"
    POISONED = "POISONED"  # stackable
    PRONE = "PRONE"
    RESTRAINED = "RESTRAINED"
    SILENCED = "SILENCED"
    STUNNED = "STUNNED"
    UNCONSCIOUS = "UNCONSCIOUS"
    EXHAUSTION = "EXHAUSTION"  # stackable - Eh? may not be used


class Disposition(Enum):
    FRIENDLY = "FRIENDLY"
    NEUTRAL = "NEUTRAL"
    AGGRESIVE = "AGGRESIVE"


class ConditionEffectInstance(BaseModel):
    """Represents an active status effect on a character"""

    effect: ConditionEffect
    duration: int  # turns remaining, -1 for permanent
    intensity: int = 1  # Bleeding, Poisioned and Exhaustion can stack
    source: Optional[str] = None  # what caused this effect
