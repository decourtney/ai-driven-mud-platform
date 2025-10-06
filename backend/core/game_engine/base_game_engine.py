import asyncio, uuid
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from abc import ABC, abstractmethod
from backend.core.game_engine.game_models import TurnPhase, GameCondition
from backend.services.api.models.scene_models import (
    GeneratedNarration,
    GenerateSceneRequest,
)
from backend.services.api.models.action_models import (
    ParseActionRequest,
    ParsedAction,
    ActionResult,
    ActionType,
    GenerateActionRequest,
    GenerateInvalidActionRequest,
    ValidationResult,
)
from backend.core.characters.character_models import CharacterType
from backend.services.ai_models.model_client import AsyncModelServiceClient
from backend.core.game_engine.game_session_manager import GameSessionManager
from backend.core.game_engine.dice_system import BaseDiceRoller
from backend.core.characters.base_character import BaseCharacter
from backend.core.characters.player_character import PlayerCharacter
from backend.core.characters.npc_character import NpcCharacter
from backend.core.scenes.scene_models import Exit
from backend.core.game_engine.game_state import GameState
from backend.core.scenes.scene_manager import SceneManager
from backend.core.game_engine.event_bus import EventBus
from backend.core.game_engine.action_validator import ActionValidator


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
        session_id: str,
        scenemanager_root_path: Optional[Path] = None,
        dice_roller: Optional[BaseDiceRoller] = None,
        **kwargs,
    ):
        self.session_id = session_id
        self.model_client = model_client
        self.session_manager = session_manager
        self.event_bus = event_bus
        self.scene_manager = (
            SceneManager(scenemanager_root_path, event_bus)
            if scenemanager_root_path
            else None
        )
        self.action_validator = ActionValidator()

        # Subscribe to scene manager events
        self.event_bus.subscribe("scene_changed", self.on_scene_diff_update)

        # Allow explicit dice roller override
        if dice_roller:
            self.dice_roller = dice_roller
        else:
            # Use game-specific default
            self.dice_roller = self.get_default_dice_roller()

        self.game_state = None
        self.player_character = None  # NOTE: Player and NPC States might be better suited for mem store on Game State
        self.npc_characters: Dict[str,] = {}
        self.is_processing = False
        self.max_invalid_attempts = kwargs.get("max_invalid_attempts", 3)

    # --------------------------------------------------------------------------------
    # Abstract Methods
    # --------------------------------------------------------------------------------

    @abstractmethod
    def get_default_dice_roller(self) -> BaseDiceRoller:
        """Each game system provides its dice roller"""
        pass

    @abstractmethod
    def convert_outcome_to_damage_type(self, outcome: str):
        """
        Convert dice system outcome to damage type.
        Must be implemented by subclasses for game-specific mappings.
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

    @abstractmethod
    def check_game_condition(self) -> GameCondition:
        """
        Check if game should continue, end in victory, or defeat.
        Must be implemented by subclasses to define win/lose conditions.
        """
        pass

    @abstractmethod
    def ai_decide_npc_action(self, npc: NpcCharacter) -> ParsedAction:
        """
        AI logic to decide NPC action.
        Must be implemented by subclasses to define game-specific NPC behavior.
        """
        pass

    # --------------------------------------------------------------------------------
    # Game State Management
    # --------------------------------------------------------------------------------

    async def load_game_state(self, game_state, player_character: Dict):
        print("[DEBUG] LOADING GAME STATE INTO ENGINE")
        try:
            self.game_state = GameState.from_db(game_state)
            # print("[DEBUG] raw game_state record:", game_state)
        except Exception as e:
            print("[ERROR] while loading GameState:", e)
            raise

        try:
            self.player_character = PlayerCharacter.from_db(player_character)
            # print("[DEBUG] raw player_character record:", player_character)
        except Exception as e:
            print("[ERROR] while loading PlayerCharacter:", e)
            raise

        await self.load_scene(
            scene_name=self.player_character.current_scene,
            zone=self.player_character.current_zone,
        )

        await self.session_manager.send_initial_state_to_session(
            self.game_state, self.player_character
        )

        print("\033[91m[DEBUG]\033[0m STARTING TURN AFTER LOADING GAME STATE")
        asyncio.create_task(self.take_turn())

    # currently only used in the game_engine_manager
    def get_serialized_game_state(self) -> Tuple[Dict, Dict]:
        print("[DEBUG] RETURNING SERIALIZED GAME STATE")
        serialized_game_state = self.game_state.to_db()
        # serialized_player_character = self.player_character # not seralizing player_character here
        return serialized_game_state, self.player_character

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # NOTE: not currently in-use
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
            result.parsed_action.actor == self.player_character.name
            or result.parsed_action.actor == "player"
        ):
            npc = self.game_state.get_npc_by_name(result.parsed_action.target)
            if npc:
                npc.apply_action_result(result)
        else:
            self.player_character.apply_action_result(result)

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # --------------------------------------------------------------------------------
    # GAME ORCHESTRATION
    # --------------------------------------------------------------------------------

    async def take_turn(self):
        """
        Start or resume a turn cycle based on persistent game_state.
        """
        # Determine phase from game_state or start fresh
        print(
            "\033[91m[DEBUG]\033[0m STARTING TURN CYCLE:",
            self.game_state.current_turn_phase,
        )
        phase = (
            TurnPhase(self.game_state.current_turn_phase)
            if self.game_state.current_turn_phase
            else TurnPhase.SCENE_NARRATION
        )

        if phase == TurnPhase.SCENE_NARRATION:
            await self.handle_scene_narration()
        elif phase == TurnPhase.PLAYER_TURN:
            await self.handle_player_turn()
        elif phase == TurnPhase.NPC_TURN:
            await self.handle_npc_turn()
        else:
            # Default: start scene narration
            await self.handle_scene_narration()

    async def determine_next_phase(self):
        """Some method to determine next phase based on game state"""
        # run through simple logic for now
        self.game_state.current_turn_phase = TurnPhase.PLAYER_TURN.value
        pass

    # Scene Narration
    async def handle_scene_narration(self):
        self.is_processing = True
        self.game_state.current_actor = None
        self.game_state.is_player_input_locked = True
        await self.session_manager.lock_player_input(
            game_state_id=self.game_state.id,
            is_locked=self.game_state.is_player_input_locked,
        )

        await self.present_scene()

        # TODO After narration determine next phase - Player / NPC / End Turn or Game Over
        await self.determine_next_phase()
        self.is_processing = False

        asyncio.create_task(self.take_turn())

    # Player Turn
    async def handle_player_turn(self):
        """
        This method unlocks the player input then
        the engine waits for a provided input action
        that triggers execute_player_action
        """
        self.game_state.current_actor = "player"
        self.game_state.is_player_input_locked = False
        await self.session_manager.lock_player_input(
            game_state_id=self.game_state.id,
            is_locked=self.game_state.is_player_input_locked,
        )

    # NPC Turn
    async def handle_npc_turn(self):
        # self.game_state.current_turn_phase = TurnPhase.NPC_TURN.value
        self.game_state.current_actor = None
        self.game_state.is_player_input_locked = True
        await self.session_manager.lock_player_input(
            game_state_id=self.game_state.id,
            is_locked=self.game_state.is_player_input_locked,
        )

        for npc in self.get_living_npcs():
            self.game_state.current_actor = npc.name
            npc_narration, condition = self.execute_single_npc_action(npc)
            await self.session_manager.send_narration(npc_narration)
            if condition != GameCondition.GAME_ON:
                await self.session_manager.end_game(condition)
                return

        # After NPCs, update scene
        # await self._update_scene_after_actions()

    def get_living_npcs(self) -> List[NpcCharacter]:
        """Get list of NPCs that can act this turn"""
        if not self.game_state:
            return []
        return [npc for npc in self.game_state.npcs if npc.is_alive()]

    # --------------------------------------------------------------------------------
    # Scene Management
    # --------------------------------------------------------------------------------

    async def load_scene(
        self,
        scene_name: str,
        zone: Optional[str] = None,
    ):
        self.game_state.loaded_scene = await self.scene_manager.get_scene(
            scene_name=scene_name, zone=zone
        )

        if self.game_state.loaded_scene.name != self.player_character.current_scene:
            self.player_character.current_scene = self.game_state.loaded_scene.name
            # We should narrate the scene since the player is arriving
            # NOTE: Not sure this is correct place to change the turn phase - works for now
            self.game_state.current_turn_phase = TurnPhase.SCENE_NARRATION
        print(
            "\033[93m[DEBUG]\033[0m CURRENT LOADED SCENE:",
            self.game_state.loaded_scene.name,
        )

        return

    # Using websocket as primary and rest as fallback
    async def present_scene(self):
        """Generate and return scene description for player"""
        if not self.game_state:
            raise RuntimeError("Game state not initialized")

        if getattr(self, "_reloading", False):
            return GeneratedNarration(
                narration="", action_type="unknown", details="Skipped during reload"
            )

        if not await self.model_client.is_narrator_ready():
            raise RuntimeError("Narrator not loaded")

        request = GenerateSceneRequest(
            scene=self.game_state.loaded_scene.model_dump(),
            player=self.player_character.model_dump(),
        )

        try:
            message_id = str(uuid.uuid4())  # Generate UUID once for this message

            # Stream the generation with proper chunk handling
            async for chunk in self.model_client.stream_scene_generation(request):
                chunk_type = chunk.get("type")

                if chunk_type == "chunk":
                    chunk_data = chunk.get("data", {})
                    text_chunk = (
                        chunk_data.get("narration", "")
                        or chunk_data.get("text", "")
                        or chunk_data.get("content", "")
                    )

                    if text_chunk:
                        # Send streaming update with consistent UUID
                        await self.session_manager.send_streaming_message(
                            message={
                                "speaker": "NARRATOR",
                                "action": "NARRATE",
                                "content": text_chunk,
                                "typing": True,
                            },
                            session_id=self.session_id,
                            message_id=message_id,
                        )

                elif chunk_type == "done":
                    message = {
                        "speaker": "NARRATOR",
                        "action": "NARRATE",
                        "content": text_chunk,
                    }

                    # Save final to DB
                    chatmessage_record = (
                        await self.session_manager.save_streamed_message(
                            message=message,
                            session_id=self.session_id,
                            message_id=message_id,
                        )
                    )

                    await self.session_manager.send_streaming_message(
                        message={"typing": False, **message},
                        session_id=self.session_id,
                        message_id=message_id,
                        timestamp=chatmessage_record.updated_at.isoformat(),
                    )
                elif chunk_type == "error":
                    error_msg = chunk.get("error", "Unknown error")
                    raise RuntimeError(f"Generation failed: {error_msg}")

            return

        except Exception as e:
            print(f"[ENGINE] WebSocket streaming failed: {e}")
            import traceback

            print(f"[ENGINE] Full traceback: {traceback.format_exc()}")

            # Fallback to REST API
            print("[ENGINE] Falling back to REST API...")
            try:
                # Serialize calls to prevent concurrent requests
                if not hasattr(self.model_client, "_model_lock"):
                    self.model_client._model_lock = asyncio.Semaphore(1)

                async with self.model_client._model_lock:
                    scene_description = await self.model_client.generate_scene(request)

                # Send the complete narration via WebSocket
                await self.session_manager.send_message_to_session(
                    session_id=self.session_id,
                    message={
                        "speaker": "NARRATOR",
                        "action": "NARRATE",
                        "content": scene_description.narration,
                        "typing": False,
                    },
                )

                return scene_description

            except Exception as fallback_error:
                print(f"[ENGINE] REST API fallback also failed: {fallback_error}")

                # Final fallback with minimal narration
                fallback_text = f"You find yourself in {self.game_state.loaded_scene.label or 'an unknown location'}."

                await self.session_manager.send_message_to_session(
                    session_id=self.session_id,
                    message={
                        "speaker": "NARRATOR",
                        "action": "NARRATE",
                        "content": fallback_text,
                        "typing": False,
                    },
                )

                return GeneratedNarration(
                    narration=fallback_text,
                    action_type="unknown",
                    details=str(fallback_error),
                )

    async def on_scene_diff_update(self, scene_name: str, diff: Dict[str, Any]):
        print(f"[EngineManager] Received scene diff for {scene_name}")

        # Engine decides whether to persist immediately or batch
        await self.session_manager.save_scene_diff(scene_name, diff)

    async def update_scene_after_actions(self):
        updated_scene, condition = await self.get_updated_scene_after_actions()
        await self.session_manager.send_narration(
            updated_scene if isinstance(updated_scene, str) else updated_scene.narration
        )

        if condition != GameCondition.GAME_ON:
            await self.session_manager.end_game(condition)
            return

        # End of turn
        self.game_state.turn_counter += 1
        self.game_state.current_turn_phase = None
        self.game_state.current_actor = None
        self.game_state.is_player_input_locked = True
        await self.session_manager.lock_player_input(
            game_state_id=self.game_state.id,
            is_locked=self.game_state.is_player_input_locked,
        )
        self.on_turn_end()

        # Ready for next turn: start scene narration for next turn
        await self.take_turn()

    # --------------------------------------------------------------------------------
    # Player Turn Execution
    # --------------------------------------------------------------------------------

    async def execute_player_action(self, action: str):
        """
        Execute a complete player turn with validation loop.
        Returns (narration_dict, game_condition)
        """
        self.is_processing = True
        invalid_attempts = 0

        while invalid_attempts < self.max_invalid_attempts:
            try:
                # Parse player input
                parsed_action = await self.model_client.parse_action(
                    ParseActionRequest(action=action, actor_type=CharacterType.PLAYER)
                )
                print("[DEBUG] Parsed Action:", parsed_action)

                # Validate action
                validation_result = await self.validate_action(
                    parsed_action=parsed_action, actor=self.player_character
                )
                print("[DEBUG] Validation Result:", validation_result)

                # If invalid request narration of invalid action
                if not validation_result.is_valid:
                    invalid_action_request = GenerateInvalidActionRequest(
                        validation_result=validation_result, parsed_action=parsed_action
                    )
                    result = await self.model_client.generate_invalid_action(
                        invalid_action_request
                    )

                    invalid_action_result = ActionResult(
                        parsed_action=parsed_action,
                        action_type=parsed_action.action_type,
                        hit=False,
                        dice_roll=0,
                        damage_type="FAILURE",
                        narration=result.narration,
                        difficulty=0,
                    )

                    invalid_action_message = {
                        "speaker": "ERROR",
                        "action": invalid_action_result.action_type.value,
                        "content": invalid_action_result.narration,
                        "player_id": self.player_character.id,
                    }

                    # Send the action result and player state to the session
                    await self.session_manager.send_player_action_to_session(
                        session_id=self.session_id,
                        message=invalid_action_message,
                        player_character=self.player_character,
                    )

                    self.is_processing = False
                    return

                if validation_result.parsed_action:
                    parsed_action = validation_result.parsed_action

                # Execute valid action
                action_result = await self.process_parsed_action(parsed_action)

                action_message = {
                    "speaker": "NARRATOR",
                    "action": action_result.action_type.value,
                    "content": action_result.narration,
                    "player_id": self.player_character.id,
                }

                # Send the action result and player state to the session
                await self.session_manager.send_player_action_to_session(
                    session_id=self.session_id,
                    message=action_message,
                    player_character=self.player_character,
                )

                # TODO: need to apply results of valid action to game state and player state

                condition = self.check_game_condition()
                self.is_processing = False
                asyncio.create_task(self.take_turn())
                return

            except Exception as e:
                return {
                    "type": "exception",
                    "message": f"An unexpected error occurred: {str(e)}",
                }, GameCondition.GAME_ON

        return {
            "type": "error",
            "message": "Unable to process action after multiple attempts.",
        }, GameCondition.GAME_ON

    # --------------------------------------------------------------------------------
    # NPC Turn Processing
    # --------------------------------------------------------------------------------

    async def execute_npc_action_with_validation(
        self, npc: NpcCharacter
    ) -> Optional[ActionResult]:
        """Execute NPC action with AI decision making and validation"""
        max_attempts = 3
        attempts = 0

        while attempts < max_attempts:
            try:
                # AI decides action
                npc_action = self.ai_decide_npc_action(npc)

                # Validate proposed action
                validation = await self.validate_action(npc_action)
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

    # ------------------------------------------------------------------------------------
    # Action Validations - will need to be abstract eventually... maybe
    # ------------------------------------------------------------------------------------

    async def validate_action(
        self, parsed_action: ParsedAction, actor: BaseCharacter
    ) -> ValidationResult:
        """Generic validation against game state (subclasses must extend)."""
        if not self.game_state:
            return ValidationResult(is_valid=False, reason="Game state not initialized")

        if not actor.can_act():
            return ValidationResult(
                is_valid=False,
                reason=f"{parsed_action.actor} is incapable of performing any actions.",
            )

        # Dynamic dispatch to specific validator
        method_name = f"validate_{parsed_action.action_type.value.lower()}_constraints"
        validator = getattr(self, method_name, None)

        if validator is None:
            return ValidationResult(
                is_valid=False,
                reason=f"No validator for {parsed_action.action_type.value}",
            )

        return await validator(parsed_action, actor)

    async def validate_movement_constraints(
        self, parsed_action: ParsedAction, actor: BaseCharacter
    ) -> ValidationResult:
        """Validate movement actions against scene data."""
        if not self.game_state:
            return ValidationResult(False, "Game state not initialized")

        # # Testing purposes only: add stunned status effect
        # actor_state.add_status_effect(
        #     effect=StatusEffect.stunned, duration=2, intensity=1, source="fear"
        # )
        # actor_state.remove_status_effect(StatusEffect.stunned)

        # Check if actor can move TODO: expand with status effects, conditions, etc.
        if not actor.can_move():
            print("\033[91m[DEBUG]\033[0m Actor cannot move due to status effects")
            return ValidationResult(
                is_valid=False,
                reason=f"{parsed_action.actor} cannot move due to current status effects.",
                suggested_action="wait until you can move again",
            )

        """
        This snippet is for determing valid exits using codellama.
        It works but a bit overkill and still uses sequence similiarity check.
        """
        # check if exit exists
        # scene_exit_request = SceneExitRequest(
        #     target=parsed_action.target, scene_exits=self.game_state.loaded_scene.exits
        # )
        # print("\033[91m[DEBUG]\033[0m Scene Exit Result:", scene_exit_request)
        # scene_exit_result = await self.model_client.determine_scene_exit(
        #     scene_exit_request
        # )
        # print("\033[91m[DEBUG]\033[0m Scene Exit Result:", scene_exit_result)

        valid_exit: Exit = self.action_validator.validate(
            query=parsed_action.target, candidates=self.game_state.loaded_scene.exits
        )
        print("\033[91m[DEBUG]\033[0m Validated exit:", valid_exit.name)

        if not valid_exit:
            return ValidationResult(is_valid=False, reason="Location doesn't exist")

        parsed_action = parsed_action.model_copy(update={"target": valid_exit.name})

        # await self.load_scene(scene_name=valid_exit.name)

        return ValidationResult(is_valid=True, parsed_action=parsed_action)

    async def validate_interact_constraints(
        self, parsed_action: ParsedAction, actor: BaseCharacter
    ) -> ValidationResult:
        return ValidationResult(is_valid=True)

    async def validate_attack_constraints(
        self, parsed_action: ParsedAction, actor: BaseCharacter
    ) -> ValidationResult:
        """Validate attack action"""
        attack_target = parsed_action.target
        if actor.character_type == CharacterType.PLAYER:
            candidates = [self.player_character]
        else:
            candidates = self.game_state.loaded_scene.npcs

        if not self.game_state:
            return ValidationResult(False, "Game state not initialized")

        valid_target: BaseCharacter = self.action_validator.validate(
            query=attack_target, candidates=candidates
        )
        print("\033[94m[DEBUG]\033[0m Valid Attack Target:", valid_target)

        # This works ok except with numbers
        # if there are multiple candidates (wolf 1, wolf 2)
        # the llm doesnt handle selection so great
        # valid_llm_target: NpcCharacter = await self.action_validator.llm_validate(
        #     query=attack_target, candidates=candidates, model_client=self.model_client
        # )
        # print("\033[94m[DEBUG]\033[0m Valid LLM Attack Target:", valid_llm_target)

        if not valid_target:
            return ValidationResult(
                is_valid=False, reason=f"No {attack_target} to attack."
            )
        if not valid_target.check_is_alive():
            return ValidationResult(
                is_valid=False, reason=f"{attack_target} is already dead."
            )

        parsed_action = parsed_action.model_copy(update={"target": valid_target.name})

        return ValidationResult(is_valid=True, parsed_action=parsed_action)

    async def validate_spell_constraints(
        self, parsed_action: ParsedAction, actor: BaseCharacter
    ) -> ValidationResult:
        return ValidationResult(is_valid=True)

    async def validate_social_constraints(
        self, parsed_action: ParsedAction, actor: BaseCharacter
    ) -> ValidationResult:
        return ValidationResult(is_valid=True)

    # --------------------------------------------------------------------------------
    # Action Processing
    # --------------------------------------------------------------------------------

    async def process_parsed_action(self, parsed_action: ParsedAction) -> ActionResult:
        """
        Process a validated action and return the result.
        Uses standardized dice system with game-specific modifiers and mappings.
        """
        if not await self.model_client.is_narrator_ready():
            raise RuntimeError("Narrator not loaded")

        # TODO: handle movement actions differently
        if parsed_action.action_type == ActionType.MOVEMENT:
            # Handle movement actions separately
            pass

        difficulty = self.get_action_difficulty(
            action_type=parsed_action.action_type, context=self.game_state
        )

        # Get any modifiers for this action (game-specific)
        modifiers = self.get_action_modifiers(parsed_action=parsed_action)

        # Roll using the game-specific dice system
        dice_result = self.dice_roller.roll_action(
            difficulty=difficulty,
            action_type=parsed_action.action_type,
            **modifiers,
        )

        # Create ActionResult from dice result
        action_result = ActionResult(
            parsed_action=parsed_action,
            action_type=parsed_action.action_type,
            hit=dice_result.hit,
            dice_roll=dice_result.total,
            damage_type=self.convert_outcome_to_damage_type(dice_result.outcome_type),
            narration="",
            difficulty=difficulty,
        )

        # Apply result and generate narration
        # self.update_game_state([action_result])

        generate_action_request = GenerateActionRequest(
            parsed_action=parsed_action,
            hit=dice_result.hit,
            damage_type=dice_result.outcome_type,
        )

        generated_action = await self.model_client.generate_action(
            generate_action_request
        )

        if generated_action.narration:
            action_result.narration = generated_action.narration or ""
        print("[DEBUG] Generated Action Narration:", action_result)

        # Hook for additional game-specific processing
        self.on_action_processed(action_result, dice_result)

        return action_result

    def get_action_modifiers(self, parsed_action: ParsedAction) -> dict:
        """
        Get modifiers for dice rolling.
        Override in subclasses for game-specific modifiers.
        """
        modifiers = {}

        # Base modifiers that most games might use
        actor_state = self.get_actor_state(
            actor_type=parsed_action.actor_type, actor_name=parsed_action.actor
        )

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
        # if self.game_state and self.game_state.loaded_scene:
        #     if self.game_state.loaded_scene.get("darkness", False):
        #         modifiers["environmental_penalty"] = -2
        #     if self.game_state.loaded_scene.get("difficult_terrain", False):
        #         modifiers["terrain_penalty"] = -1

        return modifiers

    def get_actor_state(self, actor_type: CharacterType, actor_name: str):
        """Helper to get actor state from game state"""
        # This wont work well using player name - should use character_type
        if actor_type == CharacterType.PLAYER:
            return self.player_character
        else:
            return self.npc_characters.get(actor_name, None)

    def on_action_processed(self, result: ActionResult, dice_result):
        """
        Hook called after action processing is complete.
        Override for game-specific post-processing.
        """
        pass

    # --------------------------------------------------------------------------------
    # # Utility Methods
    # --------------------------------------------------------------------------------

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
            "player_alive": self.player_character.is_alive(),
            "npcs_alive": sum(1 for npc in self.game_state.npcs if npc.is_alive()),
            "scene": self.game_state.scene.get("name", "unknown"),
        }

    # --------------------------------------------------------------------------------
    # Hook Methods for Extensibility
    # --------------------------------------------------------------------------------

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
