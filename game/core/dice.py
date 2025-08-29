from .interfaces import DiceRoller
from .models import ActionType, DamageType
import random

class StandardDiceRoller(DiceRoller):
    """Standard D&D 5e dice rolling implementation"""
    
    def roll_d20(self) -> int:
        return random.randint(1, 20)
    
    def determine_hit(self, roll: int, difficulty: int, action_type: str) -> tuple[bool, str]:
        """Determine hit and outcome type based on roll"""
        hit = roll >= difficulty
        
        if hit:
            if roll == 20:
                return True, DamageType.CRITICAL if action_type in ["attack", "spell"] else DamageType.OUTSTANDING_SUCCESS
            elif roll >= 18:
                return True, DamageType.WOUND if action_type in ["attack", "spell"] else DamageType.GREAT_SUCCESS
            else:
                return True, DamageType.WOUND if action_type in ["attack", "spell"] else DamageType.SUCCESS
        else:
            return False, DamageType.MISS if action_type in ["attack", "spell"] else DamageType.FAILURE
