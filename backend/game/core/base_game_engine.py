import asyncio
from typing import List, Optional, Tuple, Generator, Dict, Any, Callable
from pathlib import Path
from abc import ABC, abstractmethod
from enum import Enum
from backend.models import (
    ParsedAction,
    ActionResult,
    ActionType,
    GameCondition,
    ValidationResult,
    CharacterType,
    ParseActionRequest,
)
from backend.services.ai_models.model_client import AsyncModelServiceClient
from backend.game.core.game_session_manager import GameSessionManager
from backend.game.core.dice_system import BaseDiceRoller
from backend.game.core.character_state import CharacterState
from backend.game.core.game_state import GameState
from backend.game.core.scene_manager import SceneManager
from backend.game.core.event_bus import EventBus


class BaseGameEngine(ABC):
    """
    Abstract base class for turn-based game engines.
    Provides core functionality for single-player text RPGs with AI narration.
    Subclasses implement game-specific rules and mechanics.
    """

    def __init__(
        self,
        model_client: AsyncModelServiceClient,
        session_manager: GameSessionManager,
        event_bus: EventBus,
        game_id: str,
        scenemanager_root_path: Optional[Path] = None,
        dice_roller: Optional[BaseDiceRoller] = None,
        **kwargs,
    ):
        self.model_client = model_client
        self.session_manager = session_manager
        self.event_bus = event_bus
        self.scene_manager = (
            SceneManager(scenemanager_root_path, event_bus)
            if scenemanager_root_path
            else None
        )

        # Subscribe to scene manager events
        self.event_bus.subscribe("scene_changed", self.on_scene_diff_update)

        # Allow explicit dice roller override
        if dice_roller:
            self.dice_roller = dice_roller
        else:
            # Use game-specific default
            self.dice_roller = self.get_default_dice_roller()

        self.game_state = None
        self.player_state = None
        self.max_invalid_attempts = kwargs.get("max_invalid_attempts", 3)

    @abstractmethod
    def get_default_dice_roller(self) -> BaseDiceRoller:
        """Each game system provides its dice roller"""
        pass

    # ----------------------------
    # Game State Management
    # ----------------------------
    
    def load_game_state(self, game_state, player_state):
        print("[DEBUG] LOADING GAME STATE INTO ENGINE")
        try:
            self.game_state = GameState.from_db(game_state)
            # print("[DEBUG] raw game_state record:", game_state)
        except Exception as e:
            print("[ERROR] while loading GameState:", e)
            raise

        try:
            self.player_state = CharacterState.from_db(player_state)
            # print("[DEBUG] raw player_state record:", player_state)
        except Exception as e:
            print("[ERROR] while loading CharacterState:", e)
            raise

        asyncio.create_task(
            self.load_scene(
                scene_id=self.player_state.current_scene,
                zone=self.player_state.current_zone,
            )
        )

        asyncio.create_task(
            self.session_manager.send_initial_state_to_session(
                self.game_state.to_dict(), self.player_state.to_dict()
            )
        )

    def get_serialized_game_state(self) -> Tuple[Dict, Dict]:
        print("[DEBUG] RETURNING SERIALIZED GAME STATE")
        serialized_game_state = self.game_state.to_db()
        serialized_player_state = self.player_state.to_db()
        return serialized_game_state, serialized_player_state

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
        if (
            result.parsed_action.actor == self.game_state.player.name
            or result.parsed_action.actor == "player"
        ):
            npc = self.game_state.get_npc_by_name(result.parsed_action.target)
            if npc:
                npc.apply_action_result(result)
        else:
            self.game_state.player.apply_action_result(result)

    # ----------------------------
    # Scene Management
    # ----------------------------

    async def load_current_zone(self, zone_name):
        await self.scene_manager.load_zone(zone_name)

    async def load_scene(
        self,
        scene_id,
        zone: Optional[str] = None,
    ):
        self.game_state.loaded_scene = await self.scene_manager.get_scene(
            scene_id=scene_id, zone=zone
        )
        self.player_state.current_scene = self.game_state.loaded_scene.id
        print("[DEBUG] CURRENT LOADED SCENE:", self.game_state.loaded_scene.id)
        return

    async def present_scene(self) -> str:
        """Generate and return scene description for player"""
        if not self.game_state:
            raise RuntimeError("Game state not initialized")

        if not await self.model_client.is_narrator_ready():
            raise RuntimeError("Narrator not loaded")

        # Use the narrator to generate scene description based on current game state
        scene_description = self.model_client.generate_scene_narration(
            self.game_state.scene, self.game_state.player, self.game_state.npcs
        )

        return scene_description

    async def on_scene_diff_update(self, scene_id: str, diff: Dict[str, Any]):
        print(f"[EngineManager] Received scene diff for {scene_id}")

        # Engine decides whether to persist immediately or batch
        await self.session_manager.save_scene_diff(scene_id, diff)

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

    # @abstractmethod
    # def validate_action_constraints(
    #     self, parsed_action: ParsedAction
    # ) -> ValidationResult:
    #     """
    #     Validate action type specific constraints (weapons, spells, etc.).
    #     Game-specific implementation required.
    #     """
    #     pass

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
            return ValidationResult(
                False, "No actions allowed in this area", "wait for the scene to change"
            )

        blocked_exits = scene_rules.get("blocked_exits", [])
        if parsed_action.action_type == ActionType.movement:
            direction = (
                parsed_action.details.get("direction", "").lower()
                if parsed_action.details
                else ""
            )
            if direction in blocked_exits:
                return ValidationResult(
                    False,
                    f"The {direction} exit is blocked",
                    "try a different direction",
                )

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

    async def execute_player_turn(self, action: str) -> Tuple[dict, GameCondition]:
        """
        Execute a complete player turn with validation loop.
        Returns (narration_dict, game_condition)
        """
        invalid_attempts = 0

        while invalid_attempts < self.max_invalid_attempts:
            try:
                # Parse player input
                parsed_action = await self.model_client.parse_action(
                    ParseActionRequest(action=action, actor_type=CharacterType.player)
                )
                print("[DEBUG]Parsed Action:", parsed_action)
                # Validate action
                validation_result = self.validate_action(parsed_action)
                print("[DEBUG]Validation Result:", validation_result)
                if not validation_result.is_valid:
                    invalid_attempts += 1
                    error_narration = await self.model_client.generate_invalid_action(
                        validation_result
                    )
                    return {
                        "type": "error",
                        "message": error_narration.narration,
                    }, GameCondition.game_on

                # Execute valid action
                narrated_action = await self.process_parsed_action(parsed_action)

                # TODO: need to apply results of valid action to game state and player state

                condition = self.check_game_condition()
                return narrated_action, self.player_state.to_db(), condition

            except Exception as e:
                return {
                    "type": "exception",
                    "message": f"An unexpected error occurred: {str(e)}",
                }, GameCondition.game_over

        return {
            "type": "error",
            "message": "Unable to process action after multiple attempts.",
        }, GameCondition.game_on

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
            action_result = self.execute_npc_action_with_validation(npc)
            if action_result:
                # Check game condition after each action
                condition = self.check_game_condition()
                yield action_result.narration, condition

    def execute_npc_action_with_validation(
        self, npc: CharacterState
    ) -> Optional[ActionResult]:
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

    def execute_single_npc_action(
        self, npc: CharacterState
    ) -> Tuple[Optional[str], bool]:
        """
        Process a single NPC's action and return narration immediately.
        Returns (npc_narration, action_successful)
        """
        if not npc.is_alive():
            return None, False

        try:
            # AI decides action with validation
            action_result = self.execute_npc_action_with_validation(npc)
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
            return f"Error updating scene: {str(e)}", GameCondition.game_over

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
    async def process_parsed_action(self, parsed_action: ParsedAction) -> ActionResult:
        """
        Process a validated action and return the result.
        Uses standardized dice system with game-specific modifiers and mappings.
        """
        if not await self.model_client.is_narrator_ready():
            raise RuntimeError("Narrator not loaded")

        difficulty = self.get_action_difficulty(
            parsed_action.action_type, self.game_state
        )

        # Get any modifiers for this action (game-specific)
        modifiers = self.get_action_modifiers(parsed_action)

        # Roll using the game-specific dice system
        dice_result = self.dice_roller.roll_action(
            difficulty=difficulty,
            action_type=parsed_action.action_type.value,
            **modifiers,
        )

        # Create ActionResult from dice result
        result = ActionResult(
            parsed_action=parsed_action,
            action_type=parsed_action.action_type,
            hit=dice_result.hit,
            dice_roll=dice_result.total,
            damage_type=self.convert_outcome_to_damage_type(dice_result.outcome_type),
            narration="",
            difficulty=difficulty,
        )

        # Store additional dice info if ActionResult supports it
        if hasattr(result, "raw_roll"):
            result.raw_roll = dice_result.raw_roll
        if hasattr(result, "critical"):
            result.critical = dice_result.critical
        if hasattr(result, "fumble"):
            result.fumble = dice_result.fumble

        # Apply result and generate narration
        self.update_game_state([result])
        result.narration = await self.model_client.generate_action_narration(
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
        if hasattr(actor_state, "get_action_bonus"):
            modifiers["modifier"] = actor_state.get_action_bonus(
                parsed_action.action_type
            )

        # Environmental modifiers from scene
        scene_modifiers = self.get_scene_modifiers(parsed_action)
        modifiers.update(scene_modifiers)

        return modifiers

    def get_scene_modifiers(self, parsed_action: ParsedAction) -> dict:
        """Get environmental/scene-based modifiers. Can be overridden for game-specific rules."""
        modifiers = {}

        # Common environmental effects
        if self.game_state and self.game_state.scene:
            if self.game_state.scene.get("darkness", False):
                modifiers["environmental_penalty"] = -2
            if self.game_state.scene.get("difficult_terrain", False):
                modifiers["terrain_penalty"] = -1

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
        # This wont work well using player name - should use character_type
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
    def get_action_difficulty(
        self, action_type: ActionType, context: Optional[GameState] = None
    ) -> int:
        """
        Get difficulty/DC for an action type.
        Must be implemented by subclasses to define game-specific difficulty scaling.
        """
        pass

    # ----------------------------
    # Orchestration Methods for UI
    # ----------------------------
    # def get_current_scene(self) -> str:
    #     """Get current scene description (for turn start)"""
    #     try:
    #         return self.present_scene()
    #     except Exception as e:
    #         return f"Error presenting scene: {str(e)}"

    def get_living_npcs(self) -> List[CharacterState]:
        """Get list of NPCs that can act this turn"""
        if not self.game_state:
            return []
        return [npc for npc in self.game_state.npcs if npc.is_alive()]

    # ----------------------------
    # Utility Methods
    # ----------------------------
    async def is_ready(self) -> bool:
        """Check if all components are ready"""
        return (
            self.model_client.is_parser_ready()
            and await self.model_client.is_narrator_ready()
            and self.game_state is not None
        )

    def get_game_status(self) -> dict:
        """Get current game status for debugging/monitoring"""
        if not self.game_state:
            return {"status": "not_initialized"}

        return {
            "status": "active",
            "turn": self.game_state.turn_counter,
            "player_alive": self.game_state.player.is_alive(),
            "npcs_alive": sum(1 for npc in self.game_state.npcs if npc.is_alive()),
            "scene": self.game_state.scene.get("name", "unknown"),
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
