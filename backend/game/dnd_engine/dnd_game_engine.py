# Example D&D-specific implementation
from typing import Optional, Callable
from pathlib import Path
from backend.game.core.base_game_engine import BaseGameEngine
from backend.models import (
    ParsedAction,
    ActionType,
    DamageType,
    GameCondition,
    ValidationResult,
)
from backend.game.core.character_state import CharacterState
from backend.game.core.game_state import GameState
from backend.game.core.dice_system import DiceRollerFactory, BaseDiceRoller
from backend.game.core.game_session_manager import GameSessionManager
from backend.game.core.scene_manager import SceneManager
from backend.game.core.event_bus import EventBus
from backend.services.ai_models.model_client import AsyncModelServiceClient


class DnDGameEngine(BaseGameEngine):
    """
    D&D-specific implementation of the base game engine.
    Implements D&D rules for validation, action processing, and AI behavior.
    """

    def __init__(
        self,
        model_client: AsyncModelServiceClient,
        session_manager: GameSessionManager,
        event_bus: EventBus,
        game_id: str,
        **kwargs,
    ):
        scenemanager_root_path = Path(__file__).parent / "scenes" / game_id

        super().__init__(
            model_client=model_client,
            session_manager=session_manager,
            event_bus=event_bus,
            game_id=game_id,
            scenemanager_root_path=scenemanager_root_path,
            **kwargs,
        )

    def get_default_dice_roller(self) -> BaseDiceRoller:
        return DiceRollerFactory.create_roller("dnd")

    # def validate_action(self, parsed_action: ParsedAction) -> ValidationResult:
    #     """Validate action against D&D rules and current game state"""
    #     if not self.game_state:
    #         return ValidationResult(is_valid=False, reason="Game state not initialized")

    #     # Check if actor exists and is alive
    #     if parsed_action.actor == "player":
    #         if not self.player_state.is_alive():
    #             return ValidationResult(
    #                 is_valid=False, reason=f"{parsed_action.actor} is dead."
    #             )
    #     else:
    #         npc = self.game_state.get_npc_by_name(parsed_action.actor)
    #         if npc and not npc.is_alive():
    #             return ValidationResult(
    #                 is_valid=False, reason=f"{parsed_action.actor} is dead."
    #             )

    #     # Validate target exists if specified
    #     if parsed_action.target:
    #         if (
    #             parsed_action.target == self.player_state.name
    #             or parsed_action.target == "player"
    #             or parsed_action.target == "self"
    #         ):
    #             if not self.player_state.is_alive():
    #                 return ValidationResult(
    #                     is_valid=False, reason="Cannot target defeated player"
    #                 )
    #         else:
    #             target_npc = self.game_state.get_npc_by_name(parsed_action.target)
    #             if target_npc and not target_npc.is_alive():
    #                 return ValidationResult(
    #                     is_valid=False,
    #                     reason=f"{parsed_action.target} is dead",
    #                 )

    #     # Validate action type constraints
    #     validation_result = self.validate_action_constraints(parsed_action)
    #     if not validation_result.is_valid:
    #         return validation_result

    #     # Validate against scene rules
    #     scene_validation = self.validate_scene_rules(parsed_action)
    #     if not scene_validation.is_valid:
    #         return scene_validation

    #     return ValidationResult(is_valid=True)

    def validate_action(self, parsed_action: ParsedAction) -> ValidationResult:
        """Validate action against D&D rules and current game state"""
        if not self.game_state:
            return ValidationResult(is_valid=False, reason="Game state not initialized")

            # Check if actor exists and is alive
        if parsed_action.actor == "player":
            if not self.player_state.check_is_alive():
                return ValidationResult(
                    is_valid=False, reason=f"{parsed_action.actor} is dead."
                )
        else:
            npc = self.game_state.get_npc_by_name(parsed_action.actor)
            if npc and not npc.is_alive():
                return ValidationResult(
                    is_valid=False, reason=f"{parsed_action.actor} is dead."
                )

        method_name = f"validate_{parsed_action.action_type.value}_constraints"
        validator = getattr(self, method_name, None)

        if validator is None:
            return ValidationResult(
                is_valid=False,
                reason=f"No validator for {parsed_action.action_type.value}",
            )

        return validator()

    def validate_attack_constraints(self):
        return ValidationResult(is_valid=True)

    def validate_spell_constraints(self):
        return ValidationResult(is_valid=True)

    def validate_social_constraints(self):
        return ValidationResult(is_valid=True)

    def validate_movement_constraints(self):
        return ValidationResult(is_valid=True)

    def validate_interact_constraints(self):
        return ValidationResult(is_valid=True)

    # def validate_action_constraints(
    #     self, parsed_action: ParsedAction
    # ) -> ValidationResult:
    #     """Validate D&D-specific action constraints"""
    #     actor_state = (
    #         self.player_state
    #         if parsed_action.actor == "player"
    #         or parsed_action.actor == self.player_state.name
    #         else self.game_state.get_npc_by_name(parsed_action.actor)
    #     )

    #     if parsed_action.action_type == ActionType.attack:
    #         if not actor_state.equipped_weapon and not actor_state.has_natural_weapons:
    #             return ValidationResult(
    #                 is_valid=False,
    #                 reason="No weapon equipped or natural weapons available",
    #                 suggested_action="equip a weapon or use an unarmed attack",
    #             )

    #     elif parsed_action.action_type == ActionType.spell:
    #         if not actor_state.can_cast_spells():
    #             return ValidationResult(
    #                 is_valid=False,
    #                 reason="Cannot cast spells",
    #                 suggested_action="try a different action type",
    #             )
    #         if actor_state.current_mp <= 0:
    #             return ValidationResult(
    #                 is_valid=False,
    #                 reason="Not enough mana to cast spells",
    #                 suggested_action="rest to recover mana or use a different action",
    #             )

    #     elif parsed_action.action_type == ActionType.movement:
    #         if actor_state.is_immobilized():
    #             return ValidationResult(
    #                 is_valid=False,
    #                 reason="Cannot move while immobilized",
    #                 suggested_action="try to break free first",
    #             )

    #     return ValidationResult(is_valid=True)

    def validate_scene_rules(self, parsed_action: ParsedAction) -> ValidationResult:
        """Validate against D&D scene-specific rules"""
        # Call base implementation first
        base_validation = super().validate_scene_rules(parsed_action)
        if not base_validation.is_valid:
            return base_validation

        scene_rules = self.game_state.scene.get("rules", {})

        # D&D specific scene rules
        if (
            scene_rules.get("no_magic", False)
            and parsed_action.action_type == ActionType.spell
        ):
            return ValidationResult(
                is_valid=False,
                reason="Magic is suppressed in this area",
                suggested_action="try a physical attack instead",
            )

        if (
            scene_rules.get("stealth_required", False)
            and parsed_action.action_type == ActionType.attack
        ):
            if not self.player_state.has_status("stealth"):
                return ValidationResult(
                    is_valid=False,
                    reason="You must remain stealthy here",
                    suggested_action="try to hide first",
                )

        return ValidationResult(is_valid=True)

    def check_game_condition(self) -> GameCondition:
        """Check D&D win/lose conditions"""
        if not self.game_state:
            return GameCondition.game_over

        # Check player defeat
        if not self.player_state.check_is_alive():
            return GameCondition.player_defeat

        # D&D-specific victory conditions could be added here
        # For now, just continue the game
        return GameCondition.game_on

    def ai_decide_npc_action(self, npc: CharacterState) -> ParsedAction:
        """D&D-specific AI decision making for NPCs"""
        # Simple aggressive behavior for now
        if self.player_state.is_alive():
            return ParsedAction(
                actor=npc.name,
                action="attacks",
                target=self.player_state.name,
                action_type=ActionType.attack,
                weapon=npc.equipped_weapon,
                subject=None,
                details=None,
            )
        else:
            return ParsedAction(
                actor=npc.name,
                action="waits",
                target=None,
                action_type=ActionType.interact,
                weapon=None,
                subject=None,
                details=None,
            )

    def get_action_modifiers(self, parsed_action: ParsedAction) -> dict:
        """D&D-specific action modifiers"""
        modifiers = super().get_action_modifiers(parsed_action)

        # actor_state = self.get_actor_state(parsed_action.actor)

        # D&D advantage/disadvantage
        # if parsed_action.action_type == ActionType.attack:
        #     if hasattr(actor_state, "has_status"):
        #         if actor_state.has_status("flanking"):
        #             modifiers["advantage"] = True
        #         elif actor_state.has_status("prone"):
        #             modifiers["disadvantage"] = True

        # Spell attack bonuses
        # elif parsed_action.action_type == ActionType.spell:
        #     if hasattr(actor_state, "spell_attack_bonus"):
        #         modifiers["modifier"] = actor_state.spell_attack_bonus

        return modifiers

    def convert_outcome_to_damage_type(self, outcome: str):
        """Convert D&D dice outcomes to damage types"""
        # Map dice system outcomes to D&D damage types
        if hasattr(DamageType, outcome.upper()):
            return getattr(DamageType, outcome.upper())

        # Fallback mapping for common outcomes
        mapping = {
            "critical": "critical",
            "outstanding_success": "outstanding_success",
            "great_success": "great_success",
            "success": "success",
            "wound": "wound",
            "miss": "miss",
            "failure": "failure",
        }

        damage_type_name = mapping.get(outcome.lower(), "success")
        return getattr(DamageType, damage_type_name)

    def get_action_difficulty(
        self, action_type: ActionType, context: Optional[GameState] = None
    ) -> int:
        """D&D difficulty/DC values by action type with context modifiers"""
        difficulty_map = {
            ActionType.attack: 14,  # AC
            ActionType.spell: 13,  # Spell save DC
            ActionType.social: 11,  # Persuasion/Deception DC
            ActionType.movement: 8,  # Movement check DC
            ActionType.interact: 10,  # Investigation/Perception DC
        }
        base = difficulty_map.get(action_type, 12)

        return base
