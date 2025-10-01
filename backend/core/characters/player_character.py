from backend.core.characters.base_character import BaseCharacter
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from backend.core.items.item_models import Equipment, Slot, Inventory, Item
from backend.core.spells.spell_slots import SpellSlots
from backend.core.spells.spell_models import Spell
from backend.core.abilities.ability import Ability
from backend.core.quests.quest_models import QuestState


class PlayerCharacter(BaseCharacter):
    bio: str = ""
    equipment: Equipment = Equipment()
    natural_heal: str = ""  # not sure this will be implemented
    known_abilities: List[Ability] = []
    known_spells: List[Spell] = []
    spell_slots: SpellSlots = SpellSlots()
    active_quests: Dict[str, QuestState] = {}

    # ------------------------------
    # Inventory methods - thin wrappers but could be useful for effects on item pickup/drop
    # ------------------------------

    def add_to_inventory(self, item: Item):
        """Add item to inventory"""
        self.inventory.add(item)

    def remove_from_inventory(self, item_id: str) -> Optional[Item]:
        """Remove item from inventory by name"""
        self.inventory.remove(item_id)

    # ------------------------------
    # Equipment methods
    # ------------------------------

    def equip_from_inventory(self, slot: Slot, item_id: str):
        item = self.inventory.remove(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found in inventory")
        self.equipment.equip(slot, item)

    def unequip_to_inventory(self, slot: Slot):
        item = getattr(self.equipment, slot.value)
        if item:
            self.inventory.add(item)
            self.equipment.unequip(slot)

    # ------------------------------
    # Ability methods
    # ------------------------------

    def use_ability(self, ability_id: str) -> bool:
        for ability in self.known_abilities:
            if ability.id == ability_id:
                return ability.use()
        return False

    def reset_abilities(self):
        for ability in self.known_abilities:
            ability.reset_uses()

    # ------------------------------
    # Spell methods
    # ------------------------------

    def cast_spell(self, spell_id: str) -> bool:
        for spell in self.known_spells:
            if spell.id == spell_id:
                return spell.cast(self.spell_slots)
        return False
