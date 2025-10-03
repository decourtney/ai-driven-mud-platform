from pydantic import BaseModel
from typing import Optional
from enum import Enum
from backend.core.spells.spell_slots import SpellSlots


# maybe at some point?
class SpellSchool(str, Enum):
    EVOCATION = "EVOCATION"
    NECROMANCY = "NECROMANCY"
    ILLUSION = "ILLUSION"
    CONJURATION = "CONJURATION"
    TRANSMUTATION = "TRANSMUTATION"
    ABJURATION = "ABJURATION"
    DIVINATION = "DIVINATION"
    ENCHANTMENT = "ENCHANTMENT"


class Spell(BaseModel):
    id: str
    name: str
    description: str
    level: int  # 0 = cantrip, 1-9 = spell level
    cooldown: int
    school: Optional[SpellSchool] = None
    range: Optional[int] = None  # not sure about distance rn
    damage_dice: Optional[str] = None
    description: str = ""

    def cast(self, spell_slots: SpellSlots) -> bool:
        """
        Attempt to cast the spell using the provided SpellSlots instance.
        Returns True if successful, False if no slots available.
        """
        if self.level == 0:
            # Cantrips don’t use slots
            return True
        return spell_slots.use_slot(self.level)
