from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any
from backend.core.items.item_models import Item
from backend.core.items.item_models import Inventory
from backend.core.spells.spell_models import Spell
from backend.core.abilities.ability import Ability
from backend.core.characters.character_models import (
    ConditionEffectInstance,
    ConditionEffect,
    CharacterType,
    CreatureType,
)


class BaseCharacter(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    # Identity
    id: Optional[str] = None
    name: Optional[str] = None
    bio: str = ""
    character_type: CharacterType = CharacterType.NPC
    creature_type: CreatureType = CreatureType.HUMANOID
    level: int = 1

    # Core stats
    max_hp: int = 10
    current_hp: int = 10
    temporary_hp: int = 0
    armor_class: int = 10
    initiative: int = 10
    initiative_bonus: int = 0

    # Ability scores
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int

    # Equipment
    gold: int = 0
    inventory: List[Inventory] = Field(default_factory=list)

    # Skills
    known_abilities: List[Ability] = Field(default_factory=list)
    known_spells: List[Spell] = Field(default_factory=list)

    # Status effects
    condition_effects: List[ConditionEffectInstance] = Field(default_factory=list)

    # ------------------------------
    # Core status methods
    # ------------------------------
    def get_health_condition(self) -> Dict[str, Any]:
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

        return {
            "name": self.name,
            "health_status": health_status,
        }

    def check_is_alive(self) -> bool:
        """Check if character is alive"""
        return self.current_hp > 0

    def is_conscious(self) -> bool:
        """Check if character is conscious"""
        return self.check_is_alive() and not self.has_status(
            ConditionEffect.UNCONSCIOUS
        )

    def can_move(self) -> bool:
        """Check if character can move"""
        immobilizing_effects = {
            ConditionEffect.PARALYZED,
            ConditionEffect.STUNNED,
            ConditionEffect.UNCONSCIOUS,
            ConditionEffect.GRAPPLED,
            ConditionEffect.RESTRAINED,
            ConditionEffect.INCAPACITATED,
            ConditionEffect.PETRIFIED,
        }
        return self.is_conscious() and not any(
            self.has_status(effect) for effect in immobilizing_effects
        )

    def can_act(self) -> bool:
        """Check if character can make actions (attack, interact, cast, etc.)"""
        blocking_effects = {
            ConditionEffect.INCAPACITATED,
            ConditionEffect.PARALYZED,
            ConditionEffect.PETRIFIED,
            ConditionEffect.STUNNED,
            ConditionEffect.UNCONSCIOUS,
        }
        return self.is_conscious() and not any(
            self.has_status(effect) for effect in blocking_effects
        )

    def can_cast_spells(self) -> bool:
        """Check if character can cast spells"""
        return (
            self.can_act()
            and len(self.spells) > 0
            and not self.has_status(ConditionEffect.PARALYZED)
            and not self.has_status(ConditionEffect.SILENCED)
        )

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

        # May add different damage types in the future

        # Apply remaining damage to HP
        if actual_damage > 0:
            self.current_hp = max(0, self.current_hp - actual_damage)

        # Check for unconsciousness
        if self.current_hp <= 0 and not self.has_status(ConditionEffect.UNCONSCIOUS):
            self.add_status_effect(ConditionEffect.UNCONSCIOUS, -1)

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
            self.remove_status_effect(ConditionEffect.UNCONSCIOUS)

        return actual_healing

    def add_temporary_hp(self, amount: int):
        """Add temporary hit points (don't stack, take higher value)"""
        self.temporary_hp = max(self.temporary_hp, amount)
        # self.last_updated = datetime.now(timezone.utc)

    # ------------------------------
    # Status effect management
    # ------------------------------

    def has_status(self, effect: ConditionEffect) -> bool:
        """Check if character has a specific status effect"""
        return any(se.effect == effect for se in self.condition_effects)

    def get_status_effect(
        self, effect: ConditionEffect
    ) -> Optional[ConditionEffectInstance]:
        """Get specific status effect instance"""
        for se in self.condition_effects:
            if se.effect == effect:
                return se
        return None

    def add_status_effect(
        self,
        effect: ConditionEffect,
        duration: int,
        intensity: int = 1,
        source: str = None,
    ):
        """Add a status effect"""
        # Remove existing instance of same effect
        self.remove_status_effect(effect)

        # Add new effect
        effect_instance = ConditionEffectInstance(
            effect=effect, duration=duration, intensity=intensity, source=source
        )
        self.condition_effects.append(effect_instance)
        # self.last_updated = datetime.now(timezone.utc)

    def remove_status_effect(self, effect: ConditionEffect):
        """Remove a status effect"""
        self.condition_effects = [
            se for se in self.condition_effects if se.effect != effect
        ]
        # self.last_updated = datetime.now(timezone.utc)

    def update_status_effects(self):
        """Update status effect durations (call at end of turn)"""
        effects_to_remove = []

        for effect in self.condition_effects:
            if effect.duration > 0:
                effect.duration -= 1
                if effect.duration == 0:
                    effects_to_remove.append(effect.effect)

        for effect_type in effects_to_remove:
            self.remove_status_effect(effect_type)
