from enum import Enum
from typing import Optional
from pydantic import BaseModel


class AbilityType(str, Enum):
    MELEE = "melee"
    RANGED = "ranged"
    SPECIAL = "special"


class Ability(BaseModel):
    id: str
    name: str
    ability_type: AbilityType
    damage_dice: Optional[str] = None  # e.g., "1d8", "2d6+3"
    description: str = ""
    range: Optional[int] = None  # in feet/meters for ranged attacks - not sure about distance rn
    uses_per_day: Optional[int] = None  # None means unlimited
    remaining_uses: Optional[int] = None

    def use(self) -> bool:
        """
        Attempt to use the ability. Returns True if successful, False if out of uses.
        """
        if self.remaining_uses is None:
            return True
        if self.remaining_uses > 0:
            self.remaining_uses -= 1
            return True
        return False

    def reset_uses(self):
        """
        Reset remaining uses to the max (uses_per_day). If unlimited, do nothing.
        """
        if self.uses_per_day is not None:
            self.remaining_uses = self.uses_per_day
