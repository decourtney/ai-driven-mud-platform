from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
import uuid
from datetime import datetime, timezone
from backend.models import ActionResult, DamageType, ActionType, CharacterType, StatusEffect


@dataclass
class StatusEffectInstance:
    """Represents an active status effect on a character"""
    effect: StatusEffect
    duration: int  # turns remaining, -1 for permanent
    intensity: int = 1  # for effects that can stack or have varying intensity
    source: Optional[str] = None  # what caused this effect
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Item:
    """Represents an item in inventory or equipment"""
    name: str
    item_type: str  # "weapon", "armor", "consumable", "tool", etc.
    description: str = ""
    damage_dice: Optional[str] = None  # "1d8", "2d6", etc.
    armor_class: Optional[int] = None
    properties: Set[str] = field(default_factory=set)  # "magical", "heavy", "finesse", etc.
    value: int = 0  # gold value
    weight: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
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
    components: Set[str] = field(default_factory=set)  # "V", "S", "M"
    description: str = ""
    damage_dice: Optional[str] = None
    save_type: Optional[str] = None  # "Dexterity", "Wisdom", etc.
    attack_roll: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class CharacterState:
    """
    Comprehensive character state tracking health, inventory, abilities, and status.
    Supports both player characters and NPCs with full game mechanics.
    """
    
    def __init__(
        self,
        name: str,
        character_type: CharacterType = CharacterType.NPC,
        max_hp: int = 10,
        current_hp: Optional[int] = None,
        armor_class: int = 10,
        level: int = 1,
        character_class: str = "Fighter",
        background: str = "Walking Corpse",
        equipped_weapon: Optional[Item] = None, # temporary for cli mode
    ):
        # Basic identity
        self.character_id = str(uuid.uuid4())
        self.name = name
        self.character_type = character_type
        self.level = level
        self.character_class = character_class
        self.background = background
        
        # Core stats
        self.max_hp = max_hp
        self.current_hp = current_hp if current_hp is not None else max_hp
        self.temporary_hp = 0
        self.armor_class = armor_class
        
        # Ability scores (D&D standard)
        self.strength = 10
        self.dexterity = 10
        self.constitution = 10
        self.intelligence = 10
        self.wisdom = 10
        self.charisma = 10
        
        # Combat stats
        self.initiative_bonus = 0
        self.speed = 30
        self.proficiency_bonus = 2  # Based on level
        
        # Resources
        self.max_mp = 0  # Spell slots/mana
        self.current_mp = 0
        self.hit_dice = f"{level}d8"  # For healing during rest
        
        # Equipment
        self.equipped_weapon: Optional[Item] = equipped_weapon # temporary for cli mode change back to none
        self.equipped_armor: Optional[Item] = None
        self.equipped_shield: Optional[Item] = None
        self.inventory: List[Item] = []
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
        self.ai_priorities: List[str] = []  # "protect_allies", "target_spellcasters", etc.
        
        # Metadata
        self.metadata: Dict[str, Any] = {}
        self.last_updated = datetime.now()
    
    
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
            
        weapon_info = f"wielding a {self.equipped_weapon}" if self.equipped_weapon else "unarmed"
        
        return{
            "name": self.name,
            "health_status": health_status,
            "weapon": weapon_info
        }
    
    def is_alive(self) -> bool:
        """Check if character is alive"""
        return self.current_hp > 0
    
    def is_conscious(self) -> bool:
        """Check if character is conscious"""
        return self.is_alive() and not self.has_status(StatusEffect.UNCONSCIOUS)
    
    def is_enemy(self) -> bool:
        """Check if this character is an enemy"""
        return self.character_type == CharacterType.ENEMY
    
    def is_player(self) -> bool:
        """Check if this is the player character"""
        return self.character_type == CharacterType.PLAYER
    
    def debug_print(self):
        """Print detailed character state for debugging"""
        print(f"--- {self.name} ---")
        print(f"HP: {self.current_hp}/{self.max_hp} (Temp: {self.temporary_hp}), AC: {self.armor_class}")
        print("-----------------------------------")
    
    
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
            
        
        self.last_updated = datetime.now()
        
        # Check for unconsciousness
        # if self.current_hp <= 0 and not self.has_status(StatusEffect.UNCONSCIOUS):
        #     self.add_status_effect(StatusEffect.UNCONSCIOUS, -1)
        
        return actual_damage
    
    def heal(self, amount: int) -> int:
        """Heal character and return actual healing done"""
        if amount <= 0 or not self.is_alive():
            return 0
        
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        actual_healing = self.current_hp - old_hp
        
        # Remove unconscious status if healed
        if self.current_hp > 0:
            self.remove_status_effect(StatusEffect.UNCONSCIOUS)
        
        self.last_updated = datetime.now()
        return actual_healing
    
    def add_temporary_hp(self, amount: int):
        """Add temporary hit points (don't stack, take higher value)"""
        self.temporary_hp = max(self.temporary_hp, amount)
        self.last_updated = datetime.now()
    

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
    
    def add_status_effect(self, effect: StatusEffect, duration: int, intensity: int = 1, source: str = None):
        """Add a status effect"""
        # Remove existing instance of same effect
        self.remove_status_effect(effect)
        
        # Add new effect
        effect_instance = StatusEffectInstance(
            effect=effect,
            duration=duration,
            intensity=intensity,
            source=source
        )
        self.status_effects.append(effect_instance)
        self.last_updated = datetime.now()
    
    def remove_status_effect(self, effect: StatusEffect):
        """Remove a status effect"""
        self.status_effects = [se for se in self.status_effects if se.effect != effect]
        self.last_updated = datetime.now()
    
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
            StatusEffect.PARALYZED, StatusEffect.STUNNED, StatusEffect.UNCONSCIOUS,
            StatusEffect.GRAPPLED, StatusEffect.RESTRAINED
        }
        return any(self.has_status(effect) for effect in immobilizing_effects)
    
    def can_act(self) -> bool:
        """Check if character can take actions"""
        incapacitating_effects = {
            StatusEffect.STUNNED, StatusEffect.UNCONSCIOUS, StatusEffect.INCAPACITATED
        }
        return not any(self.has_status(effect) for effect in incapacitating_effects)
    
    def can_cast_spells(self) -> bool:
        """Check if character can cast spells"""
        return (self.can_act() and 
                self.current_mp > 0 and 
                len(self.known_spells) > 0 and
                not self.has_status(StatusEffect.PARALYZED))
    
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
        
        self.last_updated = datetime.now()
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
            self.armor_class = armor.armor_class + self.get_ability_modifier("dexterity")
        
        self.last_updated = datetime.now()
        return True
    
    def add_item(self, item: Item):
        """Add item to inventory"""
        self.inventory.append(item)
        self.last_updated = datetime.now()
    
    def remove_item(self, item_name: str) -> Optional[Item]:
        """Remove item from inventory by name"""
        for item in self.inventory:
            if item.name.lower() == item_name.lower():
                self.inventory.remove(item)
                self.last_updated = datetime.now()
                return item
        return None


    # ------------------------------    
    # Spell methods
    # ------------------------------
    def learn_spell(self, spell: Spell):
        """Learn a new spell"""
        if spell not in self.known_spells:
            self.known_spells.append(spell)
            self.last_updated = datetime.now()
    
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
        
        self.last_updated = datetime.now()
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
            "charisma": self.charisma
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
        
        self.last_updated = datetime.now()
        
    


    # ------------------------------    
    # Action result processing
    # ------------------------------
    def apply_action_result(self, result: ActionResult):
        """Apply the results of an action to this character"""
        if result.parsed_action.target != self.name and result.parsed_action.actor != self.name:
            return  # This result doesn't affect this character
        
        if result.hit and result.damage_type != DamageType.MISS:
            # Calculate damage based on action type and damage type
            damage = self._calculate_damage_from_result(result)
            if damage > 0:
                self.take_damage(damage, result.damage_type.value)
        
        # Apply status effects based on action type
        if result.parsed_action.action_type == ActionType.SPELL:
            self._apply_spell_effects(result)
            
        if self.current_hp <= 0 and result.damage_type != DamageType.KILL:
            result.damage_type = DamageType.KILL
        
        self.last_updated = datetime.now()
    
    def _calculate_damage_from_result(self, result: ActionResult) -> int:
        """Calculate damage from action result"""
        base_damage = 1
        
        if result.damage_type == DamageType.CRITICAL:
            base_damage = result.dice_roll  # Use actual roll for critical
        elif result.damage_type == DamageType.WOUND:
            base_damage = max(1, result.dice_roll // 4)  # Quarter of roll
        else:
            base_damage = 0
        
        return base_damage
    
    def _apply_spell_effects(self, result: ActionResult):
        """Apply spell-specific effects"""
        # This would be expanded based on specific spells
        if result.hit and "fireball" in result.parsed_action.action.lower():
            # Fire damage might cause burning
            if result.damage_type == DamageType.CRITICAL:
                self.add_status_effect(StatusEffect.CURSED, 3, source="fireball")


    # ------------------------------    
    # Serialization
    # ------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Convert character state to dictionary"""
        return {
            "character_id": self.character_id,
            "name": self.name,
            "character_type": self.character_type.value,
            "level": self.level,
            "character_class": self.character_class,
            "background": self.background,
            
            # Health
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "temporary_hp": self.temporary_hp,
            "armor_class": self.armor_class,
            
            # Ability scores
            "strength": self.strength,
            "dexterity": self.dexterity,
            "constitution": self.constitution,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "charisma": self.charisma,
            
            # Resources
            "max_mp": self.max_mp,
            "current_mp": self.current_mp,
            
            # Equipment
            "equipped_weapon": self.equipped_weapon.name if self.equipped_weapon else None,
            "equipped_armor": self.equipped_armor.name if self.equipped_armor else None,
            "inventory_count": len(self.inventory),
            "gold": self.gold,
            
            # Status
            "status_effects": [
                {
                    "effect": se.effect.value,
                    "duration": se.duration,
                    "intensity": se.intensity,
                    "source": se.source
                }
                for se in self.status_effects
            ],
            
            # State
            "is_alive": self.is_alive(),
            "can_act": self.can_act(),
            "last_updated": self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterState':
        """Create character state from dictionary"""
        character = cls(
            name=data["name"],
            character_type=CharacterType(data["character_type"]),
            max_hp=data["max_hp"],
            current_hp=data["current_hp"]
        )
        
        # Restore all attributes
        for key, value in data.items():
            if hasattr(character, key) and key not in ["status_effects", "last_updated", "character_type"]:
                setattr(character, key, value)
        
        # Restore status effects
        for effect_data in data.get("status_effects", []):
            character.add_status_effect(
                StatusEffect(effect_data["effect"]),
                effect_data["duration"],
                effect_data.get("intensity", 1),
                effect_data.get("source")
            )
            
        # Restore last_updated
        if "last_updated" in data and data["last_updated"]:
            character.last_updated = datetime.fromisoformat(data["last_updated"])
        else:
            character.last_updated = datetime.now(timezone.utc)
        
        return character


