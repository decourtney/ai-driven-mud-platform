"""
Core game engine that orchestrates parsing, dice rolling, and narration.
This is the heart of the application logic, decoupled from API concerns.
"""

import random
from typing import Optional

from .interfaces import ActionParser, ActionNarrator, DiceRoller
from .models import (
    ParsedAction, ActionResult, GameContext, ActionType, 
    DamageType, ProcessUserInputRequest
)
from .model_manager import ModelManager
from .dice import StandardDiceRoller


class GameEngine:
    """
    Main game engine that coordinates all components.
    Updated to use ModelManager for efficient model handling.
    """
    
    def __init__(
        self, 
        model_manager: ModelManager,
        dice_roller: Optional[DiceRoller] = None
    ):
        self.model_manager = model_manager
        self.dice_roller = dice_roller or StandardDiceRoller()
        
    def get_default_difficulty(self, action_type: ActionType, context: Optional[GameContext] = None) -> int:
        """Get default DC/AC for different action types, modified by context"""
        difficulty_map = {
            ActionType.ATTACK: 14,      # Average AC
            ActionType.SPELL: 13,       # Spell attack/save DC
            ActionType.SKILL_CHECK: 12, # Medium DC
            ActionType.SOCIAL: 11,      # Social interactions easier
            ActionType.MOVEMENT: 8,     # Basic movement easier
            ActionType.INTERACT: 10,    # Simple interactions
        }
        
        base_difficulty = difficulty_map.get(action_type, 12)
        
        # Apply context modifiers
        if context and context.difficulty_modifier:
            base_difficulty += context.difficulty_modifier
            
        return base_difficulty
    
    def get_game_context(self) -> Optional[GameContext]:
        """
        Retrieve or build game context from various sources.
        This is where you'd plug in context providers (database, scene manager, etc.)
        """
        # For now, just use what's in the request
        # Later this could query a scene database, character sheets, etc.
        pass
    
    def process_user_input(self, user_input: str) -> ParsedAction:
        """Process user input using ModelManager - no loading/unloading needed!"""
        if not self.model_manager.is_parser_ready():
            raise RuntimeError("Parser not loaded")
        
        return self.model_manager.parse_action(user_input)

    def process_structured_action(
        self, 
        parsed_action: ParsedAction,
        hit: bool,
        damage_type: str,
        context: Optional[GameContext] = None,
    ) -> str:
        """Process structured action using ModelManager - no loading/unloading needed!"""
        if not self.model_manager.is_narrator_ready():
            raise RuntimeError("Narrator not loaded")
        
        return self.model_manager.generate_input_narration(
            parsed_action, hit, damage_type
        )
    
    def execute_game_turn(self, request: ProcessUserInputRequest) -> ActionResult:
        """Main game loop - now much faster with persistent models!"""
        # Ensure both models are loaded
        if not self.model_manager.are_models_loaded():
            raise RuntimeError("Models not loaded")
        
        context = self.get_game_context()
        
        # Step 1: Parse (no loading/unloading - instant!)
        parsed_action = self.process_user_input(request.user_input)
        
        # Step 2: Determine difficulty and roll dice
        difficulty = self.get_default_difficulty(parsed_action.action_type, context)
        dice_roll = self.dice_roller.roll_d20()
        hit, damage_type_str = self.dice_roller.determine_hit(
            dice_roll, difficulty, parsed_action.action_type.value
        )
        
        # Step 3: Generate narration (no loading/unloading - instant!)
        narration = self.process_structured_action(parsed_action, hit, damage_type_str, context)
        
        return ActionResult(
            parsed_action=parsed_action,
            hit=hit,
            dice_roll=dice_roll,
            damage_type=DamageType(damage_type_str),
            narration=narration,
            difficulty=difficulty
        )

        
    def is_ready(self) -> dict[str, bool]:
        """Check if all components are loaded and ready"""
        parser_ready = self.model_manager.is_parser_ready()
        narrator_ready = self.model_manager.is_narrator_ready()
        
        print("Parser loaded:", parser_ready)
        print("Narrator loaded:", narrator_ready)
        
        return {
            "parser": parser_ready,
            "narrator": narrator_ready,
            "dice_roller": True,  # Dice roller is always ready
            "engine": parser_ready and narrator_ready
        }