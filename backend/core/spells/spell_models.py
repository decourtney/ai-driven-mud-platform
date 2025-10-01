from pydantic import BaseModel
from typing import Optional
from enum import Enum
from backend.core.spells.spell_slots import SpellSlots


# maybe at some point?
class SpellSchool(str, Enum):
    EVOCATION = "Evocation"
    NECROMANCY = "Necromancy"
    ILLUSION = "Illusion"
    CONJURATION = "Conjuration"
    TRANSMUTATION = "Transmutation"
    ABJURATION = "Abjuration"
    DIVINATION = "Divination"
    ENCHANTMENT = "Enchantment"


class Spell(BaseModel):
    id: str
    name: str
    level: int  # 0 = cantrip, 1-9 = spell level
    school: Optional[SpellSchool] = None
    casting_time: Optional[str] = None
    range: Optional[int] = None  # not sure about distance rn
    duration: Optional[str] = None
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
