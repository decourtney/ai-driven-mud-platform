from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field


class ItemType(str, Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    TOOL = "tool"


class Slot(str, Enum):
    HELM = "helm"
    CHEST = "chest"
    LEGS = "legs"
    HANDS = "hands"
    FEET = "feet"
    WEAPON = "weapon"
    OFF_HAND = "off_hand"


class Item(BaseModel):
    id: str
    name: str
    item_type: ItemType
    description: str = ""
    damage_dice: Optional[str] = None
    armor_class: Optional[int] = None
    gold_value: int = 0
    weight: float = 0.0

    def is_weapon(self) -> bool:
        return self.item_type == "weapon"

    def is_armor(self) -> bool:
        return self.item_type == "armor"

    def is_consumable(self) -> bool:
        return self.item_type == "consumable"


class Equipment(BaseModel):
    helm: Optional[Item] = None
    chest: Optional[Item] = None
    legs: Optional[Item] = None
    hands: Optional[Item] = None
    feet: Optional[Item] = None
    weapon: Optional[Item] = None
    off_hand: Optional[Item] = None

    def equip(self, slot: Slot, item: Item):
        setattr(self, slot.value, item)

    def unequip(self, slot: Slot):
        setattr(self, slot.value, None)


class Inventory(BaseModel):
    items: List[Item] = []

    def add(self, item: Item):
        self.items.append(item)

    def remove(self, item_id: str) -> Optional[Item]:
        for i, item in enumerate(self.items):
            if item.id == item_id:
                return self.items.pop(i)
        return None

    def find(self, item_id: str) -> Optional[Item]:
        for item in self.items:
            if item.id == item_id:
                return item
        return None


