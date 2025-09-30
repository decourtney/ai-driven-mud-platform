from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field
from backend.models import StatusEffect


class CharacterType(Enum):
    player = "player"
    npc = "npc"
    enemy = "enemy"  # Hostile NPC
    ally = "ally"


class Species(Enum):
    human = "human"
    elf = "elf"
    dwarf = "dwarf"
    orc = "orc"
    goblin = "goblin"
    troll = "troll"
    wolf = "wolf"
    bear = "bear"
    dragon = "dragon"
    skeleton = "skeleton"
    zombie = "zombie"
    slime = "slime"


class ConditionEffect(Enum):
    bleeding = "bleeding" # stackable
    blinded = "blinded"
    charmed = "charmed"
    deafened = "deafened"
    frightened = "frightened"
    grappled = "grappled"
    incapaciatated = "incapacitated"
    invisible = "invisible"
    paralyzed = "paralyzed"
    petrified = "petrified"
    poisoned = "poisoned" #stackable
    prone = "prone"
    restrained = "restrained"
    silenced = "silenced"
    stunned = "stunned"
    unconscious = "unconscious"
    exhaustion = "exhaustion" # stackable - Eh? may or may not be used


class Disposition(Enum):
    friendly = "friendly"
    neutral = "neutral"
    aggresive = "aggresive"


@dataclass
class ConditionEffectInstance:
    """Represents an active status effect on a character"""

    effect: ConditionEffect
    duration: int  # turns remaining, -1 for permanent
    intensity: int = 1  # Bleeding, Poisioned and Exhaustion can stack
    source: Optional[str] = None  # what caused this effect


@dataclass
class Item:
    """Represents an item in inventory or equipment"""

    id: str
    name: str
    item_type: str  # "weapon", "armor", "consumable", "tool", etc.
    description: str = ""
    damage_dice: Optional[str] = None  # "1d8", "2d6", etc.
    armor_class: Optional[int] = None
    # properties: Set[str] = field(default_factory=set)  # "magical", "heavy", "finesse", etc.
    gold_value: int = 0  # gold value
    weight: float = 0.0

    def is_weapon(self) -> bool:
        return self.item_type == "weapon"

    def is_armor(self) -> bool:
        return self.item_type == "armor"

    def is_consumable(self) -> bool:
        return self.item_type == "consumable"


@dataclass
class Spell:
    """Represents a spell that can be cast"""

    name: str
    level: int
    school: str  # "evocation", "illusion", etc.
    casting_time: str = "1 action"
    range_str: str = "60 feet"
    duration: str = "Instantaneous"
    description: str = ""
    damage_dice: Optional[str] = None
    save_type: Optional[str] = None  # "Dexterity", "Wisdom", etc.
    attack_roll: bool = False


@dataclass
class Ability:
    """Represents an ability that can be used"""

    name: str
