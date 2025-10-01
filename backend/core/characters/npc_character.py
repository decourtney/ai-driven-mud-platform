from pydantic import BaseModel
from typing import List, Optional
from backend.core.characters.base_character import BaseCharacter
from backend.core.characters.character_models import Disposition
from backend.core.items.item_models import Inventory, Equipment
from backend.core.abilities.ability import Ability
from backend.core.spells.spell_models import Spell
from backend.core.spells.spell_slots import SpellSlots


class NpcCharacter(BaseCharacter):
    """
    Base NPC class for all non-player characters including monsters.
    """

    disposition: Disposition = Disposition.NEUTRAL
    loot_table: Optional[List[str]] = None  # list of item IDs for randomized loot
    available_quests: Optional[List[str]] = None # quest definition ids
