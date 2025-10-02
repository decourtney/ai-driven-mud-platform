from pydantic import BaseModel
from typing import List, Optional
from backend.core.characters.base_character import BaseCharacter
from backend.core.characters.character_models import Disposition


class NpcCharacter(BaseCharacter):
    npc_id: Optional[str] = None
    base_id: Optional[str] = None
    damage: str
    disposition: Disposition = Disposition.NEUTRAL
    loot_table: Optional[List[str]] = None  # list of item IDs for randomized loot
    available_quests: Optional[List[str]] = None  # quest definition ids
