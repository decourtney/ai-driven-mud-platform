from enum import Enum
from typing import Optional, List, Dict, Union, Any
from pydantic import BaseModel
from backend.core.characters.npc_character import NpcCharacter


class SceneDiff(BaseModel):
    scene_name: str
    changes: Dict[str, Any] = {}


class Structure(BaseModel):
    name: str
    label: str
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
    requirement: Optional[str] = None
    can_lockpick: Optional[Dict] = None


class Exit(BaseModel):
    name: str
    label: str
    target_scene: str
    blocked: Optional[BlockedState] = None
    locked: Optional[LockedState] = None


class SceneItem(BaseModel):
    name: str
    label: str
    description: str
    is_interactable: bool = False
    is_loot: bool = False


class Discovery(BaseModel):
    name: str
    label: str
    observation: str
    perception_dc: int
    implication: Optional[str] = None
    quest: Optional[str] = None
    is_interactable: bool = False
    is_discovered: bool = False


# -------------------------
# Scene
# -------------------------


class Scene(BaseModel):
    name: str
    label: str
    description: str
    exits: List[Exit] = []
    structures: List[Structure] = []
    notable_npcs: List[NpcCharacter] = []
    npcs: List[NpcCharacter] = []
    items: List[SceneItem] = []
    discoveries: List[Discovery] = []

    def to_dict(self) -> dict:
        """Keeps compatibility with your old dataclass .to_dict() calls"""
        return self.model_dump(mode="json")  # ensures enums dump as values
