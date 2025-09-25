import uuid
import logging
from prisma import Json
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from backend.models import (
    ActionResult,
    DamageType,
    ActionType,
    CharacterType,
    StatusEffect,
)

logger = logging.getLogger(__name__)


@dataclass
class StatusEffectInstance:
    """Represents an active status effect on a character"""

    effect: StatusEffect
    duration: int  # turns remaining, -1 for permanent
    intensity: int = 1  # for effects that can stack or have varying intensity
    source: Optional[str] = None  # what caused this effect


@dataclass
class Item:
    """Represents an item in inventory or equipment"""

    id: str
    name: str
    item_type: str  # "weapon", "armor", "consumable", "tool", etc.
    description: str = ""
    damage_dice: Optional[str] = None  # "1d8", "2d6", etc.
    armor_class: Optional[int] = None
    # properties: Set[str] = field(default_factory=set)  # "magical", "heavy", "finesse", etc.
    gold_value: int = 0  # gold value
    weight: float = 0.0

    def is_weapon(self) -> bool:
        return self.item_type == "weapon"

    def is_armor(self) -> bool:
        return self.item_type == "armor"

    def is_consumable(self) -> bool:
        return self.item_type == "consumable"


@dataclass
class Spell:
    """Represents a spell that can be cast"""

    name: str
    level: int
    school: str  # "evocation", "illusion", etc.
    casting_time: str = "1 action"
    range_str: str = "60 feet"
    duration: str = "Instantaneous"
    # components: Set[str] = field(default_factory=set)  # "V", "S", "M"
    description: str = ""
    damage_dice: Optional[str] = None
    save_type: Optional[str] = None  # "Dexterity", "Wisdom", etc.
    attack_roll: bool = False


class CharacterState:
    """
    Comprehensive character state tracking health, inventory, abilities, and status.
    Supports both player characters and NPCs with full game mechanics.
    """

    def __init__(
        self,
        name: str,
        strength: int,
        dexterity: int,
        constitution: int,
        intelligence: int,
        wisdom: int,
        charisma: int,
        character_type: CharacterType = CharacterType.npc,
        bio: str = "Walking Corpse",
        equipped_weapon: Optional[Item] = None,
        inventory: Optional[List[Item]] = None,
    ):
        # Location
        self.current_zone = "start"
        self.current_scene = "start"

        # Basic identity
        self.id: Optional[str] = None
        self.name = name
        self.character_type = character_type
        self.level = 1
        self.bio = bio
        self.is_alive = True
        self.can_act = False

        # Core stats
        self.max_hp = 10
        self.current_hp = 10
        self.temporary_hp = 0
        self.armor_class = 10

        # Ability scores (D&D standard)
        self.strength = strength
        self.dexterity = dexterity
        self.constitution = constitution
        self.intelligence = intelligence
        self.wisdom = wisdom
        self.charisma = charisma

        # Combat stats
        self.initiative_bonus = 0
        self.speed = 30
        self.proficiency_bonus = 2  # Based on level

        # Resources
        self.max_mp = 0  # Spell slots/mana
        self.current_mp = 0
        self.hit_dice = f"{self.level}d8"  # For healing during rest

        # Equipment
        self.equipped_weapon = equipped_weapon
        self.equipped_armor = None
        self.equipped_shield = None
        self.inventory = inventory or []
        self.gold = 0

        # Spells and abilities
        self.known_spells: List[Spell] = []
        self.spell_slots: Dict[int, int] = {}  # spell level -> slots remaining
        self.abilities: List[str] = []  # Special abilities, feats, etc.

        # Status effects
        self.status_effects: List[StatusEffectInstance] = []

        # Combat state
        self.is_surprised = False
        self.has_taken_action = False
        self.has_taken_bonus_action = False
        self.has_moved = False
        self.movement_used = 0

        # AI behavior (for NPCs)
        self.ai_personality = "neutral"  # "aggressive", "defensive", "cowardly", etc.
        self.ai_priorities: List[str] = (
            []
        )  # "protect_allies", "target_spellcasters", etc.

    # For debugging changes made to character state
    # def __setattr__(self, key, value):
    #     print(f"[DEBUG] Setting {key} = {value} ({type(value)})")
    #     super().__setattr__(key, value)

    # ------------------------------
    # Core status methods
    # ------------------------------
    def get_character_condition(self) -> Dict[str, Any]:
        hp_ratio = self.current_hp / self.max_hp if self.max_hp > 0 else 0

        if hp_ratio > 0.8:
            health_status = "in excellent condition"
        elif hp_ratio > 0.5:
            health_status = "somewhat wounded"
        elif hp_ratio > 0.2:
            health_status = "badly injured"
        elif hp_ratio > 0:
            health_status = "barely standing"
        else:
            health_status = "dead"

        weapon_info = (
            f"wielding a {self.equipped_weapon}" if self.equipped_weapon else "unarmed"
        )

        return {
            "name": self.name,
            "health_status": health_status,
            "weapon": weapon_info,
        }

    def check_is_alive(self) -> bool:
        """Check if character is alive"""
        self.is_alive = self.current_hp > 0
        return self.is_alive

    def is_conscious(self) -> bool:
        """Check if character is conscious"""
        return self.check_is_alive() and not self.has_status(StatusEffect.UNCONSCIOUS)

    def is_enemy(self) -> bool:
        """Check if this character is an enemy"""
        return self.character_type == CharacterType.enemy

    def is_player(self) -> bool:
        """Check if this is the player character"""
        return self.character_type == CharacterType.player

    def debug_print(self):
        """Print detailed character state for debugging"""
        print(f"--- {self.name} ---")
        print(
            f"HP: {self.current_hp}/{self.max_hp} (Temp: {self.temporary_hp}), AC: {self.armor_class}"
        )
        print("-----------------------------------")

    def can_move(self) -> bool:
        """Check if character can move"""
        for instance in self.status_effects:
            if instance.effect in {
                StatusEffect.paralyzed,
                StatusEffect.stunned,
                StatusEffect.unconscious,
                StatusEffect.grappled,
                StatusEffect.restrained,
                StatusEffect.incapaciatated,
            }:
                return False
        pass

    # ------------------------------
    # Health management
    # ------------------------------
    def take_damage(self, damage: int, damage_type: str = "physical") -> int:
        """Apply damage and return actual damage taken"""
        if damage <= 0:
            return 0

        # Apply temporary HP first
        actual_damage = damage
        if self.temporary_hp > 0:
            temp_absorbed = min(self.temporary_hp, damage)
            self.temporary_hp -= temp_absorbed
            actual_damage -= temp_absorbed

        # Apply remaining damage to HP
        if actual_damage > 0:
            self.current_hp = max(0, self.current_hp - actual_damage)

        # self.last_updated = datetime.now(timezone.utc)

        # Check for unconsciousness
        # if self.current_hp <= 0 and not self.has_status(StatusEffect.UNCONSCIOUS):
        #     self.add_status_effect(StatusEffect.UNCONSCIOUS, -1)

        return actual_damage

    def heal(self, amount: int) -> int:
        """Heal character and return actual healing done"""
        if amount <= 0 or not self.check_is_alive():
            return 0

        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        actual_healing = self.current_hp - old_hp

        # Remove unconscious status if healed
        if self.current_hp > 0:
            self.remove_status_effect(StatusEffect.UNCONSCIOUS)

        # self.last_updated = datetime.now(timezone.utc)
        return actual_healing

    def add_temporary_hp(self, amount: int):
        """Add temporary hit points (don't stack, take higher value)"""
        self.temporary_hp = max(self.temporary_hp, amount)
        # self.last_updated = datetime.now(timezone.utc)

    # ------------------------------
    # Status effect management
    # ------------------------------
    def has_status(self, effect: StatusEffect) -> bool:
        """Check if character has a specific status effect"""
        return any(se.effect == effect for se in self.status_effects)

    def get_status_effect(self, effect: StatusEffect) -> Optional[StatusEffectInstance]:
        """Get specific status effect instance"""
        for se in self.status_effects:
            if se.effect == effect:
                return se
        return None

    def add_status_effect(
        self,
        effect: StatusEffect,
        duration: int,
        intensity: int = 1,
        source: str = None,
    ):
        """Add a status effect"""
        # Remove existing instance of same effect
        self.remove_status_effect(effect)

        # Add new effect
        effect_instance = StatusEffectInstance(
            effect=effect, duration=duration, intensity=intensity, source=source
        )
        self.status_effects.append(effect_instance)
        # self.last_updated = datetime.now(timezone.utc)

    def remove_status_effect(self, effect: StatusEffect):
        """Remove a status effect"""
        self.status_effects = [se for se in self.status_effects if se.effect != effect]
        # self.last_updated = datetime.now(timezone.utc)

    def update_status_effects(self):
        """Update status effect durations (call at end of turn)"""
        effects_to_remove = []

        for effect in self.status_effects:
            if effect.duration > 0:
                effect.duration -= 1
                if effect.duration == 0:
                    effects_to_remove.append(effect.effect)

        for effect_type in effects_to_remove:
            self.remove_status_effect(effect_type)

    # ------------------------------
    # Combat state methods
    # ------------------------------
    def is_immobilized(self) -> bool:
        """Check if character cannot move"""
        immobilizing_effects = {
            StatusEffect.PARALYZED,
            StatusEffect.STUNNED,
            StatusEffect.UNCONSCIOUS,
            StatusEffect.GRAPPLED,
            StatusEffect.RESTRAINED,
        }
        return any(self.has_status(effect) for effect in immobilizing_effects)

    def update_can_act(self) -> bool:
        """Update whether character can take actions and store in attribute."""
        incapacitating_effects = {
            StatusEffect.STUNNED,
            StatusEffect.UNCONSCIOUS,
            StatusEffect.INCAPACITATED,
        }
        self.can_act = not any(
            self.has_status(effect) for effect in incapacitating_effects
        )
        return self.can_act

    def can_cast_spells(self) -> bool:
        """Check if character can cast spells"""
        return (
            self.can_act()
            and self.current_mp > 0
            and len(self.known_spells) > 0
            and not self.has_status(StatusEffect.PARALYZED)
        )

    def reset_turn_actions(self):
        """Reset action economy for new turn"""
        self.has_taken_action = False
        self.has_taken_bonus_action = False
        self.has_moved = False
        self.movement_used = 0
        self.is_surprised = False

    # ------------------------------
    # Equipment methods
    # ------------------------------
    def equip_weapon(self, weapon: Item) -> bool:
        """Equip a weapon"""
        if not weapon.is_weapon():
            return False

        # Unequip current weapon
        if self.equipped_weapon:
            self.inventory.append(self.equipped_weapon)

        self.equipped_weapon = weapon
        if weapon in self.inventory:
            self.inventory.remove(weapon)

        # self.last_updated = datetime.now(timezone.utc)
        return True

    def equip_armor(self, armor: Item) -> bool:
        """Equip armor"""
        if not armor.is_armor():
            return False

        # Unequip current armor
        if self.equipped_armor:
            self.inventory.append(self.equipped_armor)

        self.equipped_armor = armor
        if armor in self.inventory:
            self.inventory.remove(armor)

        # Update AC
        if armor.armor_class:
            self.armor_class = armor.armor_class + self.get_ability_modifier(
                "dexterity"
            )

        # self.last_updated = datetime.now(timezone.utc)
        return True

    def add_item(self, item: Item):
        """Add item to inventory"""
        self.inventory.append(item)
        # self.last_updated = datetime.now(timezone.utc)

    def remove_item(self, item_name: str) -> Optional[Item]:
        """Remove item from inventory by name"""
        for item in self.inventory:
            if item.name.lower() == item_name.lower():
                self.inventory.remove(item)
                # self.last_updated = datetime.now(timezone.utc)
                return item
        return None

    # ------------------------------
    # Spell methods
    # ------------------------------
    def learn_spell(self, spell: Spell):
        """Learn a new spell"""
        if spell not in self.known_spells:
            self.known_spells.append(spell)
            # self.last_updated = datetime.now(timezone.utc)

    def can_cast_spell(self, spell: Spell) -> bool:
        """Check if character can cast a specific spell"""
        if not self.can_cast_spells() or spell not in self.known_spells:
            return False

        # Check spell slots
        spell_slots_available = self.spell_slots.get(spell.level, 0)
        return spell_slots_available > 0

    def cast_spell(self, spell: Spell) -> bool:
        """Cast a spell (consumes resources)"""
        if not self.can_cast_spell(spell):
            return False

        # Consume spell slot
        self.spell_slots[spell.level] -= 1
        self.current_mp = max(0, self.current_mp - 1)

        # self.last_updated = datetime.now(timezone.utc)
        return True

    # ------------------------------
    # Ability score methods
    # ------------------------------
    def get_ability_modifier(self, ability: str) -> int:
        """Get ability score modifier"""
        ability_scores = {
            "strength": self.strength,
            "dexterity": self.dexterity,
            "constitution": self.constitution,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "charisma": self.charisma,
        }

        score = ability_scores.get(ability.lower(), 10)
        return (score - 10) // 2

    def set_ability_score(self, ability: str, value: int):
        """Set an ability score"""
        if ability.lower() == "strength":
            self.strength = value
        elif ability.lower() == "dexterity":
            self.dexterity = value
        elif ability.lower() == "constitution":
            self.constitution = value
        elif ability.lower() == "intelligence":
            self.intelligence = value
        elif ability.lower() == "wisdom":
            self.wisdom = value
        elif ability.lower() == "charisma":
            self.charisma = value

        # self.last_updated = datetime.now(timezone.utc)

    # ------------------------------
    # Action result processing
    # ------------------------------
    def apply_action_result(self, result: ActionResult):
        """Apply the results of an action to this character"""
        if (
            result.parsed_action.target != self.name
            and result.parsed_action.actor != self.name
        ):
            return  # This result doesn't affect this character

        if result.hit and result.damage_type != DamageType.miss:
            # Calculate damage based on action type and damage type
            damage = self._calculate_damage_from_result(result)
            if damage > 0:
                self.take_damage(damage, result.damage_type.value)

        # Apply status effects based on action type
        if result.parsed_action.action_type == ActionType.spell:
            self._apply_spell_effects(result)

        if self.current_hp <= 0 and result.damage_type != DamageType.kill:
            result.damage_type = DamageType.kill

        # self.last_updated = datetime.now(timezone.utc)

    def _calculate_damage_from_result(self, result: ActionResult) -> int:
        """Calculate damage from action result"""
        base_damage = 1

        if result.damage_type == DamageType.critical:
            base_damage = result.dice_roll  # Use actual roll for critical
        elif result.damage_type == DamageType.wound:
            base_damage = max(1, result.dice_roll // 4)  # Quarter of roll
        else:
            base_damage = 0

        return base_damage

    def _apply_spell_effects(self, result: ActionResult):
        """Apply spell-specific effects"""
        # This would be expanded based on specific spells
        if result.hit and "fireball" in result.parsed_action.action.lower():
            # Fire damage might cause burning
            if result.damage_type == DamageType.critical:
                self.add_status_effect(StatusEffect.CURSED, 3, source="fireball")

    # ------------------------------
    # DB CONVERSION
    # ------------------------------

    @classmethod
    def from_db(cls, record) -> "CharacterState":
        obj = cls(
            name=record.name,
            strength=record.strength,
            dexterity=record.dexterity,
            constitution=record.constitution,
            intelligence=record.intelligence,
            wisdom=record.wisdom,
            charisma=record.charisma,
            character_type=CharacterType(record.character_type),
            bio=record.bio or "Walking Corpse",
        )

        obj.id = record.id
        obj.level = record.level
        obj.gold = record.gold

        obj.max_hp = record.max_hp
        obj.current_hp = record.current_hp
        obj.temporary_hp = record.temporary_hp
        obj.armor_class = record.armor_class

        obj.max_mp = record.max_mp
        obj.current_mp = record.current_mp

        # Update status dynamically if needed
        obj.is_alive
        obj.can_act

        obj.current_zone = record.current_zone
        obj.current_scene = record.current_scene

        # Initialize JSON fields
        obj.equipped_armor = record.equipped_armor or None
        obj.equipped_weapon = record.equipped_weapon or None
        obj.inventory = record.inventory or []
        obj.status_effects = record.status_effects or []

        return obj

    def to_db(self, for_create: bool = False) -> dict:
        data = {
            "name": self.name,
            "strength": self.strength,
            "dexterity": self.dexterity,
            "constitution": self.constitution,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "charisma": self.charisma,
            "level": self.level,
            "gold": self.gold,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "temporary_hp": self.temporary_hp,
            "armor_class": self.armor_class,
            "max_mp": self.max_mp,
            "current_mp": self.current_mp,
            "is_alive": self.is_alive,
            "can_act": self.can_act,
            "character_type": self.character_type.value,
            "bio": self.bio,
            "current_zone": self.current_zone,
            "current_scene": self.current_scene,
            "inventory": Json(self.inventory or []),
            "equipped_weapon": Json(self.equipped_weapon or {}),
            "equipped_armor": Json(self.equipped_armor or {}),
            "status_effects": Json(self.status_effects or []),
        }

        if not for_create:
            data["id"] = self.id
            # optionally include last_updated or other fields for update

        return data

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "strength": self.strength,
            "dexterity": self.dexterity,
            "constitution": self.constitution,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "charisma": self.charisma,
            "level": self.level,
            "gold": self.gold,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "temporary_hp": self.temporary_hp,
            "armor_class": self.armor_class,
            "max_mp": self.max_mp,
            "current_mp": self.current_mp,
            "is_alive": self.is_alive,
            "can_act": self.can_act,
            "character_type": self.character_type.value,
            "bio": self.bio,
            "current_zone": self.current_zone,
            "current_scene": self.current_scene,
            "inventory": self.inventory or [],
            "equipped_weapon": self.equipped_weapon or {},
            "equipped_armor": self.equipped_armor or {},
            "status_effects": self.status_effects or [],
        }

    # ------------------------------
    # Serialization
    # ------------------------------

    # def to_dict(self) -> Dict[str, Any]:
    #     """Convert character state to dictionary with robust error handling"""
    #     try:
    #         return {
    #             "current_zone": getattr(self, "current_zone", ""),
    #             "current_scene": getattr(self, "current_scene", ""),
    #             "name": self.name,
    #             "character_type": (
    #                 self.character_type.value
    #                 if self.character_type and hasattr(self.character_type, "value")
    #                 else str(self.character_type) if self.character_type else "NPC"
    #             ),
    #             "level": getattr(self, "level", 1),
    #             "bio": self.bio,
    #             "max_hp": getattr(self, "max_hp", 100),
    #             "current_hp": getattr(self, "current_hp", 100),
    #             "temporary_hp": getattr(self, "temporary_hp", 0),
    #             "armor_class": getattr(self, "armor_class", 10),
    #             "strength": self.strength,
    #             "dexterity": self.dexterity,
    #             "constitution": self.constitution,
    #             "intelligence": self.intelligence,
    #             "wisdom": self.wisdom,
    #             "charisma": self.charisma,
    #             "max_mp": getattr(self, "max_mp", 50),
    #             "current_mp": getattr(self, "current_mp", 50),
    #             "equipped_weapon": self._serialize_item(self.equipped_weapon),
    #             "equipped_armor": self._serialize_item(getattr(self, "equipped_armor")),
    #             "inventory": self._serialize_inventory(),
    #             "gold": getattr(self, "gold", 0),
    #             "status_effects": self._serialize_status_effects(),
    #             "is_alive": self._safe_is_alive(),
    #             "can_act": self._safe_can_act(),
    #         }
    #     except Exception as e:
    #         logging.error(
    #             f"Error serializing CharacterState {getattr(self, 'name', 'Unknown')}: {e}"
    #         )
    #         raise

    # def _serialize_item(self, item) -> Optional[Dict[str, Any]]:
    #     """Safely serialize an item"""
    #     if not item:
    #         return Json({})

    #     try:
    #         # Handle different item structures
    #         if hasattr(item, "to_dict"):
    #             return item.to_dict()
    #         elif hasattr(item, "name"):
    #             # Basic item serialization
    #             result = {"name": self._get_value(item.name)}

    #             # Add common item fields if they exist
    #             for field in [
    #                 "item_type",
    #                 "description",
    #                 "damage_dice",
    #                 "armor_class",
    #                 "gold_value",
    #                 "weight",
    #             ]:
    #                 if hasattr(item, field):
    #                     result[field] = self._get_value(getattr(item, field))

    #             return result
    #         else:
    #             # Fallback: treat as string
    #             return {"name": str(item)}

    #     except Exception as e:
    #         logging.warning(f"Error serializing item: {e}")
    #         return {"name": str(item) if item else "Unknown Item"}

    # def _serialize_inventory(self) -> List[Dict[str, Any]]:
    #     """Safely serialize inventory"""
    #     if not hasattr(self, "inventory") or not self.inventory:
    #         return Json([])

    #     serialized_items = []
    #     for item in self.inventory:
    #         try:
    #             serialized_item = self._serialize_item(item)
    #             if serialized_item:
    #                 serialized_items.append(serialized_item)
    #         except Exception as e:
    #             logging.warning(f"Skipping problematic inventory item: {e}")
    #             continue

    #     return serialized_items

    # def _serialize_status_effects(self) -> List[Dict[str, Any]]:
    #     """Safely serialize status effects"""
    #     if not hasattr(self, "status_effects") or not self.status_effects:
    #         return Json([])

    #     serialized_effects = []
    #     for se in self.status_effects:
    #         try:
    #             effect_dict = {
    #                 "effect": self._get_value(getattr(se, "effect", "unknown")),
    #                 "duration": getattr(se, "duration", 0),
    #                 "intensity": getattr(se, "intensity", 1),
    #                 "source": getattr(se, "source", ""),
    #             }
    #             serialized_effects.append(effect_dict)
    #         except Exception as e:
    #             logging.warning(f"Error serializing status effect: {e}")
    #             continue

    #     return serialized_effects

    # def _get_value(self, obj):
    #     """Safely extract value from objects that might have .value attribute"""
    #     if hasattr(obj, "value"):
    #         return obj.value
    #     return obj

    # def _safe_is_alive(self) -> bool:
    #     """Safely check if character is alive"""
    #     try:
    #         if hasattr(self, "is_alive") and callable(self.check_is_alive):
    #             return self.check_is_alive()
    #         # Fallback logic
    #         current_hp = getattr(self, "current_hp", 100)
    #         return current_hp > 0
    #     except Exception:
    #         return True  # Default assumption

    # def _safe_can_act(self) -> bool:
    #     """Safely check if character can act"""
    #     try:
    #         if hasattr(self, "can_act") and callable(self.can_act):
    #             return self.can_act()
    #         # Fallback logic
    #         return self._safe_is_alive()
    #     except Exception:
    #         return True  # Default assumption

    # @classmethod
    # def from_dict(cls, data: Dict[str, Any]) -> "CharacterState":
    #     """Restore character from dictionary with robust error handling"""
    #     try:
    #         # Validate required fields
    #         required_fields = [
    #             "name",
    #             "id",
    #             "strength",
    #             "dexterity",
    #             "constitution",
    #             "intelligence",
    #             "wisdom",
    #             "charisma",
    #         ]
    #         missing_fields = [field for field in required_fields if field not in data]
    #         if missing_fields:
    #             raise ValueError(f"Missing required fields: {missing_fields}")

    #         # Handle character_type safely
    #         character_type = None
    #         if "character_type" in data:
    #             try:
    #                 # Assuming you have a CharacterType enum/class
    #                 # from your_enums import CharacterType  # Replace with actual import

    #                 if isinstance(data["character_type"], str):
    #                     character_type = CharacterType(data["character_type"])
    #                 else:
    #                     character_type = data["character_type"]
    #             except Exception as e:
    #                 logging.warning(
    #                     f"Error loading character_type: {e}. Using default."
    #                 )
    #                 character_type = None  # or CharacterType.NPC

    #         # Create character with core fields
    #         character = cls(
    #             name=data["name"],
    #             strength=int(data["strength"]),
    #             dexterity=int(data["dexterity"]),
    #             constitution=int(data["constitution"]),
    #             intelligence=int(data["intelligence"]),
    #             wisdom=int(data["wisdom"]),
    #             charisma=int(data["charisma"]),
    #             character_type=character_type,
    #             bio=data.get("bio", ""),
    #         )

    #         # Fields to skip during automatic restoration
    #         SKIP_KEYS = {
    #             "name",
    #             "strength",
    #             "dexterity",
    #             "constitution",
    #             "intelligence",
    #             "wisdom",
    #             "charisma",
    #             "character_type",
    #             "bio",
    #             "status_effects",
    #             "last_updated",
    #             "inventory",
    #             "equipped_weapon",
    #             "equipped_armor",
    #             "is_alive",
    #             "can_act",
    #         }

    #         # Restore simple attributes with type checking
    #         simple_field_types = {
    #             "current_scene": str,
    #             "level": int,
    #             "max_hp": int,
    #             "current_hp": int,
    #             "temporary_hp": int,
    #             "armor_class": int,
    #             "max_mp": int,
    #             "current_mp": int,
    #             "gold": int,
    #         }

    #         for key, expected_type in simple_field_types.items():
    #             try:
    #                 value = data.get(key)
    #                 if value is not None:
    #                     # Type conversion with fallback
    #                     if expected_type == int:
    #                         setattr(
    #                             character, key, int(float(value))
    #                         )  # Handle "100.0" -> 100
    #                     elif expected_type == str:
    #                         setattr(character, key, str(value))
    #                     else:
    #                         setattr(character, key, value)
    #             except (ValueError, TypeError) as e:
    #                 logging.warning(f"Error converting {key}: {e}. Using default.")
    #                 # Default values are already set in __init__

    #         # Restore equipment
    #         character.equipped_weapon = cls._deserialize_item(
    #             data.get("equipped_weapon")
    #         )
    #         character.equipped_armor = cls._deserialize_item(data.get("equipped_armor"))
    #         character.inventory = cls._deserialize_inventory(data.get("inventory", []))

    #         # Restore status effects
    #         character.status_effects = []
    #         for effect_data in data.get("status_effects", []):
    #             try:
    #                 character.add_status_effect(
    #                     StatusEffect(effect_data["effect"]),
    #                     effect_data.get("duration", 0),
    #                     effect_data.get("intensity", 1),
    #                     effect_data.get("source", ""),
    #                 )
    #             except Exception as e:
    #                 logging.warning(f"Error restoring status effect: {e}")

    #         # Restore timestamp
    #         try:
    #             last_updated_str = data.get("last_updated")
    #             character.last_updated = (
    #                 datetime.fromisoformat(last_updated_str)
    #                 if last_updated_str
    #                 else datetime.now(timezone.utc)
    #             )
    #         except Exception as e:
    #             logging.warning(f"Error parsing last_updated: {e}")
    #             character.last_updated = datetime.now(timezone.utc)

    #         return character

    #     except Exception as e:
    #         logging.error(f"Critical error deserializing CharacterState: {e}")
    #         raise

    @staticmethod
    def _deserialize_item(item_data) -> Optional["Item"]:
        """Safely deserialize an item"""
        if not item_data:
            return None

        try:
            # If it's just a string (old format), create a basic item
            if isinstance(item_data, str):
                # You'll need to replace this with your actual Item creation
                return Item(name=item_data)

            # If it's a dict, try to recreate the item
            if isinstance(item_data, dict):
                # Replace this with your actual Item.from_dict method
                return Item.from_dict(item_data)

            return None

        except Exception as e:
            logging.warning(f"Error deserializing item: {e}")
            return None

    @staticmethod
    def _deserialize_inventory(inventory_data: List[Dict[str, Any]]) -> List["Item"]:
        """Safely deserialize inventory"""
        if not inventory_data:
            return []

        items = []
        for item_data in inventory_data:
            try:
                item = CharacterState._deserialize_item(item_data)
                if item:
                    items.append(item)
            except Exception as e:
                logging.warning(f"Skipping problematic inventory item: {e}")
                continue

        return items
