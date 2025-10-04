from backend.core.characters.base_character import BaseCharacter
from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Dict, List, Optional, Any
from backend.core.items.item_models import Equipment, Slot, Item, Inventory
from backend.core.spells.spell_slots import SpellSlots
from backend.core.spells.spell_models import Spell
from backend.core.abilities.ability import Ability
from backend.core.quests.quest_models import QuestState
from backend.core.characters.character_models import (
    CharacterType,
    CreatureType,
    ConditionEffectInstance,
)


class PlayerCharacter(BaseCharacter):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: Optional[str] = None
    base_id: Optional[str] = None
    experience: int = 0
    equipment: Equipment = Field(default_factory=Equipment)
    natural_heal: str = ""  # not sure this will be implemented
    spell_slots: SpellSlots = Field(
        default_factory=SpellSlots
    )  # spell_slots=SpellSlots(max_slots={1:3, 2:1}) - 3 level 1 slots, 1 level 2 slot
    active_quests: Dict[str, QuestState] = Field(default_factory=dict)
    current_zone: Optional[str] = "start"
    current_scene: Optional[str] = "start"

    @model_validator(mode="before")
    def set_initial_hp(cls, values):
        con = values.get("constitution", 10)
        level = values.get("level", 1)
        # Simple formula: 10 base + con modifier per level
        con_mod = (con - 10) // 2
        values["max_hp"] = 10 + max(con_mod * level, 0)
        values["current_hp"] = values["max_hp"]
        return values

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

    @classmethod
    def from_db(cls, record: Dict):
        base_data = record["base"]
        return cls(
            id=record["id"],
            base_id=base_data["id"],
            name=base_data["name"],
            bio=base_data["bio"],
            character_type=CharacterType(base_data["character_type"]),
            creature_type=CreatureType(base_data["creature_type"]),
            level=record["level"],
            max_hp=record["max_hp"],
            current_hp=record["current_hp"],
            temporary_hp=record["temporary_hp"],
            armor_class=record["armor_class"],
            initiative=record["initiative"],
            initiative_bonus=record["initiative_bonus"],
            strength=record["strength"],
            dexterity=record["dexterity"],
            constitution=record["constitution"],
            intelligence=record["intelligence"],
            wisdom=record["wisdom"],
            charisma=record["charisma"],
            gold=record["gold"],
            condition_effects=[
                ConditionEffectInstance(**ce) for ce in base_data["condition_effects"]
            ],
            inventory=[Inventory(**i) for i in base_data["inventory"]],
            known_abilities=[Ability(**a) for a in base_data["abilities"]],
            known_spells=[Spell(**s) for s in base_data["spells"]],
            spell_slots=SpellSlots.from_db(record["spell_slots"]),
            active_quests={
                q["quest_id"]: QuestState.from_db(q) for q in record["active_quests"]
            },
            experience=record["experience"],
            natural_heal=record["natural_heal"],
            current_zone=record["current_zone"],
            current_scene=record["current_scene"],
        )
