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


class InventoryItem(BaseModel):
    id: Optional[str] = None  # ID of the inventory row in DB
    item_id: str  # references Item.id
    quantity: int = 1
    equipped: bool = False
    slot: Optional[Slot] = None


class Inventory(BaseModel):
    items: List[InventoryItem] = []

    def add(self, inv_item: InventoryItem):
        self.items.append(inv_item)

    def remove(self, inventory_id: str) -> Optional[InventoryItem]:
        for i, inv_item in enumerate(self.items):
            if inv_item.id == inventory_id:
                return self.items.pop(i)
        return None

    def find(self, inventory_id: str) -> Optional[InventoryItem]:
        for inv_item in self.items:
            if inv_item.id == inventory_id:
                return inv_item
        return None

    def find_by_item_id(self, item_id: str) -> Optional[InventoryItem]:
        for inv_item in self.items:
            if inv_item.item_id == item_id:
                return inv_item
        return None
