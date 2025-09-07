from typing import List, Optional, Tuple, Generator, Dict, Any
from abc import ABC, abstractmethod
from enum import Enum

from backend.models import (
    ParsedAction, ActionResult, ActionType, 
    GameCondition, ValidationResult
)
from backend.services.ai_models.model_client import AsyncModelServiceClient
from backend.game.core.dice_system import BaseDiceRoller
from backend.game.core.character_state import CharacterState
from backend.game.core.game_state import GameState


class BaseGameEngine(ABC):
    """
    Abstract base class for turn-based game engines.
    Provides core functionality for single-player text RPGs with AI narration.
    Subclasses implement game-specific rules and mechanics.
    """

    def __init__(self, model_client: AsyncModelServiceClient, dice_roller: Optional[BaseDiceRoller] = None, **kwargs):
        self.model_client = model_client

        # Allow explicit dice roller override
        if dice_roller:
            self.dice_roller = dice_roller
        else:
            # Use game-specific default
            self.dice_roller = self.get_default_dice_roller()

        self.game_state = None
        self.max_invalid_attempts = kwargs.get('max_invalid_attempts', 3)

    @abstractmethod
    def get_default_dice_roller(self) -> BaseDiceRoller:
        """Each game system provides its dice roller"""
        pass

    # ----------------------------
    # Game State Management
    # ----------------------------
    def create_game_state(self, player_state: Dict[str, Any]):
        """Create initial GameState with player, NPCs, and scene data"""

        # this feels janky but fuck it for now
        # If wrapped in `player_state` key from API
        if "player_state" in player_state:
            player_state = player_state["player_state"]
        # Flatten nested stats if present
        if "stats" in player_state:
            player_state.update(player_state.pop("stats"))

        player_state_obj = CharacterState.from_dict(player_state)

        initial_scene = {
            "id": "intro",
            "title": "Introduction",
            "description": "And so it begins..."
        }

        self.game_state = GameState(
            player=player_state_obj,
            npcs=[],
            scene=initial_scene,
            turn_counter=0,
        )

        serialized_game_state = self.game_state.to_dict()

        return serialized_game_state

    def load_game_state(self, game_state: GameState):
        pass

    def update_game_state(self, results: List[ActionResult]):
        """Apply results of actions to game state"""
        if not self.game_state:
            raise RuntimeError("Game state not initialized")

        for result in results:
            self._apply_action_result_to_state(result)

        self.game_state.turn_counter += 1

    def _apply_action_result_to_state(self, result: ActionResult):
        """Apply a single action result to the game state"""
        # Update player or NPC based on who acted
        if result.parsed_action.actor == self.game_state.player.name or result.parsed_action.actor == "player":
            npc = self.game_state.get_npc_by_name(result.parsed_action.target)
            if npc:
                npc.apply_action_result(result)
        else:
            self.game_state.player.apply_action_result(result)

    # ----------------------------
    # Scene Management
    # ----------------------------
    def present_scene(self) -> str:
        """Generate and return scene description for player"""
        if not self.game_state:
            raise RuntimeError("Game state not initialized")

        if not self.model_manager.is_narrator_ready():
            raise RuntimeError("Narrator not loaded")

        # Use the narrator to generate scene description based on current game state
        scene_description = self.model_manager.generate_scene_narration(
            self.game_state.scene,
            self.game_state.player,
            self.game_state.npcs
        )

        return scene_description

    # ----------------------------
    # Abstract Action Validation
    # ----------------------------
    @abstractmethod
    def validate_action(self, parsed_action: ParsedAction) -> ValidationResult:
        """
        Validate action against current game state and game rules.
        Must be implemented by subclasses to define game-specific validation.
        """
        pass

    @abstractmethod
    def validate_action_constraints(self, parsed_action: ParsedAction) -> ValidationResult:
        """
        Validate action type specific constraints (weapons, spells, etc.).
        Game-specific implementation required.
        """
        pass

    def validate_scene_rules(self, parsed_action: ParsedAction) -> ValidationResult:
        """
        Validate against scene-specific rules.
        Base implementation handles common scene rules, can be extended.
        """
        if not self.game_state:
            return ValidationResult(False, "Game state not initialized")

        scene_rules = self.game_state.scene.get("rules", {})

        # Generic scene rule validations that most games might use
        if scene_rules.get("no_actions", False):
            return ValidationResult(False, "No actions allowed in this area", "wait for the scene to change")

        blocked_exits = scene_rules.get("blocked_exits", [])
        if parsed_action.action_type == ActionType.MOVEMENT:
            direction = parsed_action.details.get("direction", "").lower() if parsed_action.details else ""
            if direction in blocked_exits:
                return ValidationResult(False, f"The {direction} exit is blocked", "try a different direction")

        return ValidationResult(True)

    # ----------------------------
    # Abstract Game Condition Checking
    # ----------------------------
    @abstractmethod
    def check_game_condition(self) -> GameCondition:
        """
        Check if game should continue, end in victory, or defeat.
        Must be implemented by subclasses to define win/lose conditions.
        """
        pass

    # ----------------------------
    # Player Turn Processing
    # ----------------------------
    def execute_player_turn(self, user_action: str) -> Tuple[str, GameCondition]:
        """
        Execute complete player turn with validation loop.
        Returns (narration, game_condition)
        """
        invalid_attempts = 0

        while invalid_attempts < self.max_invalid_attempts:
            try:
                # Parse player input
                parsed_action = self.model_manager.parse_action(user_action)

                # Validate action
                validation_result = self.validate_action(parsed_action)
                if not validation_result.is_valid:
                    invalid_attempts += 1
                    error_narration = self.model_manager.generate_invalid_action_narration(
                        validation_result
                    )

                    if invalid_attempts >= self.max_invalid_attempts:
                        return f"{error_narration}\n\nToo many invalid attempts. Turn skipped.", GameCondition.CONTINUE
                    else:
                        return f"{error_narration}\n\nTry again.", GameCondition.CONTINUE

                # Execute valid action
                result = self.process_parsed_action(parsed_action)

                # Check game condition after player action
                condition = self.check_game_condition()

                return result.narration, condition

            except Exception as e:
                return f"An error occurred: {str(e)}", GameCondition.GAME_OVER

        return "Unable to process action after multiple attempts.", GameCondition.CONTINUE

    # ----------------------------
    # NPC Turn Processing
    # ----------------------------
    def execute_npc_turn(self) -> Generator[Tuple[str, GameCondition], None, None]:
        """
        Execute NPC turns one at a time with validation and AI decision making.
        Yields (narration, game_condition) after each NPC acts.
        """
        if not self.game_state:
            raise RuntimeError("Game state not initialized")

        for npc in self.game_state.npcs:
            if not npc.is_alive():
                continue

            # AI decides action with validation loop
            action_result = self._execute_npc_action_with_validation(npc)
            if action_result:
                # Check game condition after each action
                condition = self.check_game_condition()
                yield action_result.narration, condition

    def _execute_npc_action_with_validation(self, npc: CharacterState) -> Optional[ActionResult]:
        """Execute NPC action with AI decision making and validation"""
        max_attempts = 3
        attempts = 0

        while attempts < max_attempts:
            try:
                # AI decides action
                npc_action = self.ai_decide_npc_action(npc)

                # Validate proposed action
                validation = self.validate_action(npc_action)
                if validation.is_valid:
                    # Execute valid action
                    return self.process_parsed_action(npc_action)
                else:
                    attempts += 1
                    continue

            except Exception as e:
                attempts += 1
                continue

        return None  # NPC turn failed after max attempts

    def execute_single_npc_action(self, npc: CharacterState) -> Tuple[Optional[str], bool]:
        """
        Process a single NPC's action and return narration immediately.
        Returns (npc_narration, action_successful)
        """
        if not npc.is_alive():
            return None, False

        try:
            # AI decides action with validation
            action_result = self._execute_npc_action_with_validation(npc)
            if action_result:
                # Apply this NPC's action immediately
                self.update_game_state([action_result])
                return action_result.narration, True
            else:
                return f"{npc.name} hesitates, unable to act.", False

        except Exception as e:
            return f"{npc.name} encounters an error: {str(e)}", False

    def get_updated_scene_after_actions(self) -> Tuple[str, GameCondition]:
        """
        Generate updated scene description after all actions are processed.
        Returns (scene_description, final_game_condition)
        """
        try:
            scene_description = self.present_scene()
            final_condition = self.check_game_condition()
            return scene_description, final_condition

        except Exception as e:
            return f"Error updating scene: {str(e)}", GameCondition.GAME_OVER

    # ----------------------------
    # Abstract AI Decision Making
    # ----------------------------
    @abstractmethod
    def ai_decide_npc_action(self, npc: CharacterState) -> ParsedAction:
        """
        AI logic to decide NPC action.
        Must be implemented by subclasses to define game-specific NPC behavior.
        """
        pass

    # ----------------------------
    # Action Processing
    # ----------------------------
    def process_parsed_action(self, parsed_action: ParsedAction) -> ActionResult:
        """
        Process a validated action and return the result.
        Uses standardized dice system with game-specific modifiers and mappings.
        """
        if not self.model_manager.is_narrator_ready():
            raise RuntimeError("Narrator not loaded")

        difficulty = self.get_action_difficulty(parsed_action.action_type, self.game_state)

        # Get any modifiers for this action (game-specific)
        modifiers = self.get_action_modifiers(parsed_action)

        # Roll using the game-specific dice system
        dice_result = self.dice_roller.roll_action(
            difficulty=difficulty,
            action_type=parsed_action.action_type.value,
            **modifiers
        )

        # Create ActionResult from dice result
        result = ActionResult(
            parsed_action=parsed_action,
            hit=dice_result.hit,
            dice_roll=dice_result.total,
            damage_type=self.convert_outcome_to_damage_type(dice_result.outcome_type),
            narration="",
            difficulty=difficulty
        )

        # Store additional dice info if ActionResult supports it
        if hasattr(result, 'raw_roll'):
            result.raw_roll = dice_result.raw_roll
        if hasattr(result, 'critical'):
            result.critical = dice_result.critical
        if hasattr(result, 'fumble'):
            result.fumble = dice_result.fumble

        # Apply result and generate narration
        self.update_game_state([result])
        result.narration = self.model_manager.generate_action_narration(
            parsed_action, dice_result.hit, dice_result.outcome_type
        )

        # Hook for additional game-specific processing
        self.on_action_processed(result, dice_result)

        return result

    def get_action_modifiers(self, parsed_action: ParsedAction) -> dict:
        """
        Get modifiers for dice rolling. 
        Override in subclasses for game-specific modifiers.
        """
        modifiers = {}

        # Base modifiers that most games might use
        actor_state = self.get_actor_state(parsed_action.actor)
        if hasattr(actor_state, 'get_action_bonus'):
            modifiers['modifier'] = actor_state.get_action_bonus(parsed_action.action_type)

        # Environmental modifiers from scene
        scene_modifiers = self.get_scene_modifiers(parsed_action)
        modifiers.update(scene_modifiers)

        return modifiers

    def get_scene_modifiers(self, parsed_action: ParsedAction) -> dict:
        """Get environmental/scene-based modifiers. Can be overridden for game-specific rules."""
        modifiers = {}

        # Common environmental effects
        if self.game_state and self.game_state.scene:
            if self.game_state.scene.get('darkness', False):
                modifiers['environmental_penalty'] = -2
            if self.game_state.scene.get('difficult_terrain', False):
                modifiers['terrain_penalty'] = -1

        return modifiers

    @abstractmethod 
    def convert_outcome_to_damage_type(self, outcome: str):
        """
        Convert dice system outcome to damage type. 
        Must be implemented by subclasses for game-specific mappings.
        """
        pass

    def get_actor_state(self, actor_name: str):
        """Helper to get actor state from game state"""
        if actor_name == "player":
            return self.game_state.player
        else:
            return self.game_state.get_npc_by_name(actor_name)

    def on_action_processed(self, result: ActionResult, dice_result):
        """
        Hook called after action processing is complete.
        Override for game-specific post-processing.
        """
        pass

    @abstractmethod
    def get_action_difficulty(self, action_type: ActionType, context: Optional[GameState] = None) -> int:
        """
        Get difficulty/DC for an action type.
        Must be implemented by subclasses to define game-specific difficulty scaling.
        """
        pass

    # ----------------------------
    # Orchestration Methods for UI
    # ----------------------------
    def get_current_scene(self) -> str:
        """Get current scene description (for turn start)"""
        try:
            return self.present_scene()
        except Exception as e:
            return f"Error presenting scene: {str(e)}"

    def get_living_npcs(self) -> List[CharacterState]:
        """Get list of NPCs that can act this turn"""
        if not self.game_state:
            return []
        return [npc for npc in self.game_state.npcs if npc.is_alive()]

    # ----------------------------
    # Utility Methods
    # ----------------------------
    def is_ready(self) -> bool:
        """Check if all components are ready"""
        return (self.model_manager.is_parser_ready() and 
                self.model_manager.is_narrator_ready() and 
                self.game_state is not None)

    def get_game_status(self) -> dict:
        """Get current game status for debugging/monitoring"""
        if not self.game_state:
            return {"status": "not_initialized"}

        return {
            "status": "active",
            "turn": self.game_state.turn_counter,
            "player_alive": self.game_state.player.is_alive(),
            "npcs_alive": sum(1 for npc in self.game_state.npcs if npc.is_alive()),
            "scene": self.game_state.scene.get("name", "unknown")
        }

    # ----------------------------
    # Hook Methods for Extensibility
    # ----------------------------
    def on_turn_start(self):
        """Called at the start of each turn. Override for game-specific logic."""
        pass

    def on_turn_end(self):
        """Called at the end of each turn. Override for game-specific logic."""
        pass

    def on_action_executed(self, result: ActionResult):
        """Called after each action is executed. Override for game-specific logic."""
        pass

    def on_game_state_changed(self):
        """Called whenever game state changes. Override for game-specific logic."""
        pass
