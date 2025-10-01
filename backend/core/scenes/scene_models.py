from enum import Enum
from typing import Optional, List, Dict, Union, Any
from pydantic import BaseModel
from backend.core.characters.character_models import Disposition


class SceneDiff(BaseModel):
    scene_id: str
    changes: Dict[str, Any] = {}


class Status(BaseModel):
    is_alive: bool = True
    is_hostile: bool = False
    health: int = 10


class Structure(BaseModel):
    id: str
    name: str
    description: str


class Requirement(BaseModel):
    strength_dc: Optional[int] = None
    dexterity_dc: Optional[int] = None
    key: Optional[str] = None


class BlockedState(BaseModel):
    active: bool
    reason: Optional[str] = None
    can_unblock: Optional[Dict] = None


class LockedState(BaseModel):
    active: bool
    requirement: Optional[Union[Requirement, str]] = None
    can_lockpick: Optional[Dict] = None


class Exit(BaseModel):
    id: str
    label: str
    target_scene: str
    blocked: Optional[BlockedState] = None
    locked: Optional[LockedState] = None


class Item(BaseModel):
    id: str
    name: str
    description: str
    is_interactable: bool = False
    is_loot: bool = False


class Discovery(BaseModel):
    id: str
    type: str
    observation: str
    perception_dc: int
    implication: Optional[str] = None
    quest: Optional[str] = None
    is_interactable: bool = False
    is_discovered: bool = False


class NPC(BaseModel):
    id: str
    name: str
    description: str
    status: Status
    disposition: Disposition = Disposition.NEUTRAL


class NotableNPC(NPC):
    """For special dialogue or quest-related NPCs"""

    pass


# -------------------------
# Scene
# -------------------------


class Scene(BaseModel):
    id: str
    label: str
    description: str
    exits: List[Exit] = []
    structures: List[Structure] = []
    notable_npcs: List[NotableNPC] = []
    npcs: List[NPC] = []
    items: List[Item] = []
    discoveries: List[Discovery] = []

    def to_dict(self) -> dict:
        """Keeps compatibility with your old dataclass .to_dict() calls"""
        return self.model_dump(mode="json")  # ensures enums dump as values
