"""
Abstract interfaces for the D&D narrator system.
This allows easy swapping of implementations and testing.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from .models import ParsedAction, ActionResult


class ActionParser(ABC):
    """Abstract base class for action parsers"""
    
    @abstractmethod
    def load_model(self) -> bool:
        """Load the parser model/resources"""
        pass
    
    def unload_model(self) -> bool:
        """Unload the model to free resources"""
        pass
    
    @abstractmethod
    def parse_action(self, user_input: str) -> ParsedAction:
        """Parse natural language input into structured action"""
        pass
    
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if parser is ready to use"""
        pass


class ActionNarrator(ABC):
    """Abstract base class for action narrators"""
    
    @abstractmethod
    def load_model(self) -> bool:
        """Load the narrator model/resources"""
        pass
    
    def unload_model(self) -> bool:
        """Unload the model to free resources"""
        pass
    
    @abstractmethod
    def generate_input_narration(self, action: ParsedAction, dice_roll: int, 
                          hit: bool, damage_type: str = "wound") -> str:
        """Generate narrative description of an action"""
        pass
    
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if narrator is ready to use"""
        pass


class DiceRoller(ABC):
    """Abstract base class for dice rolling systems"""
    
    @abstractmethod
    def roll_d20(self) -> int:
        """Roll a d20"""
        pass
    
    @abstractmethod
    def determine_hit(self, roll: int, difficulty: int, action_type: str) -> tuple[bool, str]:
        """Determine if roll succeeds and what type of result"""
        pass