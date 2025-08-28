from typing import List, Optional, Tuple, Generator
from enum import Enum

from .interfaces import ActionParser, ActionNarrator, DiceRoller
from .models import (
    ParsedAction, ActionResult, GameContext, ActionType, 
    DamageType, ProcessUserInputRequest, GameCondition, ValidationResult
)
from .model_manager import ModelManager
from .dice import StandardDiceRoller
from .character_state import CharacterState
from .game_state import GameState


class GameEngine:
    """
    Turn-based game engine skeleton for single-player text RPG.
    Player and NPC actions are processed sequentially with full validation and scene management.
    """
    
    def __init__(
        self,
        model_manager: ModelManager,
        dice_roller: Optional[DiceRoller] = None,
        max_invalid_attempts: int = 3
    ):
        self.model_manager = model_manager
        self.dice_roller = dice_roller or StandardDiceRoller()
        self.game_state: Optional[GameState] = None
        self.max_invalid_attempts = max_invalid_attempts

    # ----------------------------
    # Game State Management
    # ----------------------------
    def initialize_game_state(self, player_state: CharacterState, npcs: List[CharacterState], scene_state: dict):
        """Create initial GameState with player, NPCs, and scene data"""
        self.game_state = GameState(
            player=player_state,
            npcs=npcs,
            scene=scene_state,
            turn_counter=0,
            global_flags={}
        )

    def update_game_state(self, results: List[ActionResult]):
        """Apply results of actions to game state"""
        if not self.game_state:
            raise RuntimeError("Game state not initialized")
        
        for result in results:
            # Update player or NPC HP, status, inventory, etc.
            if result.parsed_action.actor == self.game_state.player.name or result.parsed_action.actor == "player":
                npc = self.game_state.get_npc_by_name(result.parsed_action.target)
                if npc:
                    npc.apply_action_result(result)
            else:
                self.game_state.player.apply_action_result(result)
        
        self.game_state.turn_counter += 1

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
    # Action Validation
    # ----------------------------
    def validate_action(self, parsed_action: ParsedAction) -> ValidationResult:
        """Validate action against current game state and scene rules"""
        if not self.game_state:
            return ValidationResult(False, "Game state not initialized")

        # Check if actor exists and is alive
        if parsed_action.actor == "player":
            if not self.game_state.player.is_alive():
                return ValidationResult(False, "Player is defeated and cannot act")
        else:
            npc = self.game_state.get_npc_by_name(parsed_action.actor)
            if not npc or not npc.is_alive():
                return ValidationResult(False, f"NPC {parsed_action.actor} is not available")

        # Validate target exists if specified
        if parsed_action.target:
            if parsed_action.target == self.game_state.player.name or parsed_action.target == "player":
                if not self.game_state.player.is_alive():
                    return ValidationResult(False, "Cannot target defeated player")
            elif parsed_action.target != "self":
                target_npc = self.game_state.get_npc_by_name(parsed_action.target)
                if not target_npc:
                    return ValidationResult(False, f"Target {parsed_action.target} not found")

        # Validate action type constraints
        validation_result = self._validate_action_constraints(parsed_action)
        if not validation_result.is_valid:
            return validation_result

        # Validate against scene rules
        scene_validation = self._validate_scene_rules(parsed_action)
        if not scene_validation.is_valid:
            return scene_validation

        return ValidationResult(True)

    def _validate_action_constraints(self, parsed_action: ParsedAction) -> ValidationResult:
        """Validate action type specific constraints"""
        actor_state = self.game_state.player if parsed_action.actor == "player" else self.game_state.get_npc_by_name(parsed_action.actor)
        
        if parsed_action.action_type == ActionType.ATTACK:
            if not actor_state.equipped_weapon and not actor_state.has_natural_weapons:
                return ValidationResult(False, "No weapon equipped or natural weapons available", "equip a weapon or use an unarmed attack")
        
        elif parsed_action.action_type == ActionType.SPELL:
            if not actor_state.can_cast_spells():
                return ValidationResult(False, "Cannot cast spells", "try a different action type")
            if actor_state.current_mp <= 0:
                return ValidationResult(False, "Not enough mana to cast spells", "rest to recover mana or use a different action")
        
        elif parsed_action.action_type == ActionType.MOVEMENT:
            if actor_state.is_immobilized():
                return ValidationResult(False, "Cannot move while immobilized", "try to break free first")
        
        return ValidationResult(True)

    def _validate_scene_rules(self, parsed_action: ParsedAction) -> ValidationResult:
        """Validate against scene-specific rules"""
        scene_rules = self.game_state.scene.get("rules", {})
        
        # Example scene rule validations
        if scene_rules.get("no_magic", False) and parsed_action.action_type == ActionType.SPELL:
            return ValidationResult(False, "Magic is suppressed in this area", "try a physical attack instead")
        
        if scene_rules.get("stealth_required", False) and parsed_action.action_type == ActionType.ATTACK:
            if not self.game_state.player.has_status("stealth"):
                return ValidationResult(False, "You must remain stealthy here", "try to hide first")
        
        blocked_exits = scene_rules.get("blocked_exits", [])
        if parsed_action.action_type == ActionType.MOVEMENT:
            direction = parsed_action.details.get("direction", "").lower() if parsed_action.details else ""
            if direction in blocked_exits:
                return ValidationResult(False, f"The {direction} exit is blocked", "try a different direction")
        
        return ValidationResult(True)


    # ----------------------------
    # Game Condition Checking
    # ----------------------------
    def check_game_condition(self) -> GameCondition:
        """Check if game should continue, end in victory, or defeat"""
        if not self.game_state:
            return GameCondition.GAME_OVER
        
        # Check player defeat
        if not self.game_state.player.is_alive():
            return GameCondition.PLAYER_DEFEAT
        
        # ----------
        # Victory conditions - should this be per scene or for whole game?
        # ----------
        # all_enemies_defeated = all(not npc.is_alive() for npc in self.game_state.npcs if npc.is_enemy())
        # if all_enemies_defeated:
        #     # Check for specific win conditions in scene
        #     win_conditions = self.game_state.scene.get("win_conditions", {})
        #     if win_conditions.get("defeat_all_enemies", True):
        #         return GameCondition.PLAYER_WIN
        
        # # Check scene-specific win/lose conditions
        # if self.game_state.scene.get("objective_complete", False):
        #     return GameCondition.PLAYER_WIN
        
        # if self.game_state.scene.get("objective_failed", False):
        #     return GameCondition.PLAYER_DEFEAT
        
        return GameCondition.CONTINUE


    # ----------------------------
    # Complete Player Turn
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
                        # In a real game, you'd get new input here
                        return f"{error_narration}\n\nTry again.", GameCondition.CONTINUE
                
                # Execute valid action
                result = self._processed_parced_action(parsed_action)
                # self.update_game_state([result])
                
                # Check game condition after player action
                condition = self.check_game_condition()
                
                return result.narration, condition
                
            except Exception as e:
                return f"An error occurred: {str(e)}", GameCondition.GAME_OVER

        return "Unable to process action after multiple attempts.", GameCondition.CONTINUE


    # ----------------------------
    # Complete NPC Turn
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
                # Update game state after each NPC action
                # self.update_game_state([action_result])

                # Check game condition after each action
                condition = self.check_game_condition()

                yield action_result.narration, condition

    def _execute_npc_action_with_validation(self, npc: CharacterState) -> Optional[ActionResult]:
        """Execute NPC action with AI decision making and validation"""
        max_attempts = 3
        attempts = 0
        
        while attempts < max_attempts:
            try:
                # AI decides action (placeholder - replace with actual AI logic)
                npc_action = self._ai_decide_npc_action(npc)
                
                # Validate proposed action
                validation = self.validate_action(npc_action)
                if validation.is_valid:
                    # Execute valid action
                    return self._processed_parced_action(npc_action)
                else:
                    attempts += 1
                    # AI could learn from validation failure here
                    continue
                    
            except Exception as e:
                attempts += 1
                continue
        
        return None  # NPC turn failed after max attempts

    # This is a placeholder AI decision function and needs a lot more sophistication
    def _ai_decide_npc_action(self, npc: CharacterState) -> ParsedAction:
        """AI logic to decide NPC action (placeholder for now)"""
        # This is where you'd implement sophisticated AI decision making
        # For now, simple aggressive behavior
        if self.game_state.player.is_alive():
            return ParsedAction(
                actor=npc.name,
                action="attacks",
                target=self.game_state.player.name,
                action_type=ActionType.ATTACK,
                weapon=npc.equipped_weapon,
                subject=None,
                details=None
            )
        else:
            return ParsedAction(
                actor=npc.name,
                action="waits",
                target=None,
                action_type=ActionType.INTERACT,
                weapon=None,
                subject=None,
                details=None
            )


    # ----------------------------
    # Core Action Processing
    # ----------------------------
    def _processed_parced_action(self, parsed_action: ParsedAction) -> ActionResult:
        """Parse player input, roll dice, and generate narration (existing method enhanced)"""
        if not self.model_manager.is_narrator_ready():
            raise RuntimeError("Narrator not loaded")

        difficulty = self.get_default_difficulty(parsed_action.action_type, self.game_state)
        
        # Dice rolls and hit determination is in a base state and need to be expanded
        dice_roll = self.dice_roller.roll_d20()
        hit, damage_type_str = self.dice_roller.determine_hit(dice_roll, difficulty, parsed_action.action_type.value)
        
        # Create preliminary ActionResult without narration
        result = ActionResult(
            parsed_action=parsed_action,
            hit=hit,
            dice_roll=dice_roll,
            damage_type=DamageType(damage_type_str),
            narration="",
            difficulty=difficulty
        )
        
        # Apply this result immediately so state is updated before narration
        self.update_game_state([result])
              
        result.narration = self.model_manager.generate_input_narration(parsed_action, hit, damage_type_str)
          
        print("-----------------------------------")
        print('--- Action Result ---')
        print(f'   {parsed_action.actor} {result.damage_type.value} {parsed_action.target}')
        print("-----------------------------------")
        
        self.game_state.player.debug_print()
        for npc in self.game_state.npcs:
            npc.debug_print()
        
        return result


    # ----------------------------
    # Streaming Game Loop Components
    # ----------------------------
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
        This runs while other processing happens in background.
        Returns (scene_description, final_game_condition)
        """
        try:
            # Generate fresh scene description
            scene_description = self.present_scene()
            
            # Final condition check
            final_condition = self.check_game_condition()
            
            return scene_description, final_condition
            
        except Exception as e:
            return f"Error updating scene: {str(e)}", GameCondition.GAME_OVER

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
    def get_default_difficulty(self, action_type: ActionType, context: Optional[GameState] = None) -> int:
        """Default DC/AC values by action type with context modifiers"""
        difficulty_map = {
            ActionType.ATTACK: 14,
            ActionType.SPELL: 13,
            ActionType.SKILL_CHECK: 12,
            ActionType.SOCIAL: 11,
            ActionType.MOVEMENT: 8,
            ActionType.INTERACT: 10,
        }
        base = difficulty_map.get(action_type, 12)
        
        # Apply context modifiers
        if context:
            # Scene difficulty modifiers
            scene_modifier = context.scene.get("difficulty_modifier", 0)
            base += scene_modifier
            
            # Environmental modifiers
            if context.scene.get("darkness", False):
                base += 2
            if context.scene.get("difficult_terrain", False):
                base += 1
                
        return base

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