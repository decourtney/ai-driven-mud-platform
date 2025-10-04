from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict
from backend.core.characters.base_character import BaseCharacter
from backend.core.characters.character_models import Disposition


class NpcCharacter(BaseCharacter):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: Optional[str] = None
    base_id: Optional[str] = None
    damage: str
    disposition: Disposition = Disposition.NEUTRAL
    loot_table: Optional[List[str]] = None  # list of item IDs for randomized loot
    available_quests: Optional[List[str]] = None  # quest definition ids

    @classmethod
    def from_db(cls, record: Dict):
        base_data = record["base"]
        return cls()
