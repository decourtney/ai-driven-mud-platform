from fastapi import Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field


# -------------------------
# Scene and Exit structures
# -------------------------


class Disposition(Enum):
    friendly = "friendly"
    neutral = "neutral"
    aggresive = "aggresive"


@dataclass
class Exit:
    id: str
    label: str
    target_scene: str
    is_locked: Optional[bool] = None
    zone: Optional[str] = None


@dataclass
class SceneDiff:
    scene_id: str
    changes: dict = field(default_factory=dict)


@dataclass
class Structure:
    id: str
    name: str
    description: str


@dataclass
class Status:
    is_alive: bool = True
    is_hostile: bool = False
    health: int = 10


@dataclass
class NotableNPC:
    id: str
    name: str
    description: str
    status: Status
    disposition: Disposition


@dataclass
class NPC:
    id: str
    name: str
    description: str
    status: Status
    disposition: Disposition


@dataclass
class Item:
    id: str
    name: str
    description: str
    is_interactable: bool = False
    is_loot: bool = False


@dataclass
class Discovery:
    id: str
    type: str
    observation: str
    perception_dc: int
    implication: Optional[str] = None
    quest: Optional[str] = None
    is_interactable: bool = False
    is_discovered: bool = False


@dataclass
class Requirement:
    strength_dc: int | None = None
    dexterity_dc: int | None = None
    key: str | None = None

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class BlockedState:
    active: bool
    reason: str | None = None
    can_unblock: dict | None = None  # or another dataclass

    def to_dict(self):
        return {
            "active": self.active,
            "reason": self.reason,
            "can_unblock": self.can_unblock,
        }


@dataclass
class LockedState:
    active: bool
    requirement: str | Requirement | None = None
    can_lockpick: dict | None = None

    def to_dict(self):
        return {
            "active": self.active,
            "requirement": (
                self.requirement.to_dict()
                if isinstance(self.requirement, Requirement)
                else self.requirement
            ),
            "can_lockpick": self.can_lockpick,
        }


@dataclass
class Exit:
    id: str
    label: str
    target_scene: str
    blocked: BlockedState
    locked: LockedState

    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "target_scene": self.target_scene,
            "blocked": self.blocked.to_dict(),
            "locked": self.locked.to_dict(),
        }


@dataclass
class Scene:
    id: str
    label: str
    description: str
    exits: list[Exit] = field(default_factory=list)
    structures: list[Structure] = field(default_factory=list)
    notable_npcs: list[NotableNPC] = field(default_factory=list)
    npcs: list[NPC] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)
    discoveries: list[Discovery] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "exits": [e.to_dict() for e in self.exits],
            "structures": [s.__dict__ for s in self.structures],
            "notable_npcs": [
                {
                    **n.__dict__,
                    "status": n.status.__dict__,
                    "disposition": n.disposition.value,
                }
                for n in self.notable_npcs
            ],
            "npcs": [
                {
                    **n.__dict__,
                    "status": n.status.__dict__,
                    "disposition": n.disposition.value,
                }
                for n in self.npcs
            ],
            "items": [i.__dict__ for i in self.items],
            "discoveries": [d.__dict__ for d in self.discoveries],
        }
