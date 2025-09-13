import random
from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Any, Optional
from enum import Enum

from backend.game.core.interfaces import DiceRoller
from backend.models import ActionType, DamageType


class DiceResult:
    """Standardized result from any dice roll system"""

    def __init__(
        self,
        raw_roll: int | List[int],
        total: int,
        hit: bool,
        outcome_type: str,
        critical: bool = False,
        fumble: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.raw_roll = raw_roll
        self.total = total
        self.hit = hit
        self.outcome_type = outcome_type
        self.critical = critical
        self.fumble = fumble
        self.metadata = metadata or {}


class BaseDiceRoller(DiceRoller, ABC):
    """
    Abstract base class for dice rolling systems.
    Provides common dice rolling utilities while allowing game-specific implementations.
    """

    def __init__(self, random_seed: Optional[int] = None):
        if random_seed is not None:
            random.seed(random_seed)

    # ----------------------------
    # Basic Dice Rolling (Common)
    # ----------------------------
    def roll_die(self, sides: int) -> int:
        """Roll a single die with specified number of sides"""
        return random.randint(1, sides)

    def roll_dice(self, count: int, sides: int) -> List[int]:
        """Roll multiple dice and return all results"""
        return [self.roll_die(sides) for _ in range(count)]

    def roll_dice_sum(self, count: int, sides: int, modifier: int = 0) -> int:
        """Roll multiple dice and return the sum plus modifier"""
        return sum(self.roll_dice(count, sides)) + modifier

    def roll_d4(self) -> int:
        return self.roll_die(4)

    def roll_d6(self) -> int:
        return self.roll_die(6)

    def roll_d8(self) -> int:
        return self.roll_die(8)

    def roll_d10(self) -> int:
        return self.roll_die(10)

    def roll_d12(self) -> int:
        return self.roll_die(12)

    def roll_d20(self) -> int:
        return self.roll_die(20)

    def roll_d100(self) -> int:
        return self.roll_die(100)

    def roll_percentile(self) -> int:
        """Roll percentile dice (00-99)"""
        tens = (self.roll_d10() - 1) * 10  # 0, 10, 20, ..., 90
        ones = self.roll_d10() - 1  # 0, 1, 2, ..., 9
        return tens + ones

    # ----------------------------
    # Advanced Rolling Techniques
    # ----------------------------
    def roll_with_advantage(self, sides: int) -> Tuple[int, List[int]]:
        """Roll twice, take the higher (D&D advantage)"""
        rolls = self.roll_dice(2, sides)
        return max(rolls), rolls

    def roll_with_disadvantage(self, sides: int) -> Tuple[int, List[int]]:
        """Roll twice, take the lower (D&D disadvantage)"""
        rolls = self.roll_dice(2, sides)
        return min(rolls), rolls

    def roll_exploding(
        self, sides: int, explode_on: Optional[int] = None
    ) -> Tuple[int, List[int]]:
        """
        Exploding dice - if you roll max value, roll again and add.
        explode_on: specific value to explode on (defaults to max)
        """
        if explode_on is None:
            explode_on = sides

        total = 0
        all_rolls = []

        while True:
            roll = self.roll_die(sides)
            all_rolls.append(roll)
            total += roll

            if roll != explode_on:
                break

        return total, all_rolls

    def roll_keep_highest(
        self, count: int, sides: int, keep: int
    ) -> Tuple[int, List[int]]:
        """Roll multiple dice, keep only the highest N"""
        rolls = self.roll_dice(count, sides)
        kept = sorted(rolls, reverse=True)[:keep]
        return sum(kept), rolls

    def roll_keep_lowest(
        self, count: int, sides: int, keep: int
    ) -> Tuple[int, List[int]]:
        """Roll multiple dice, keep only the lowest N"""
        rolls = self.roll_dice(count, sides)
        kept = sorted(rolls)[:keep]
        return sum(kept), rolls

    def roll_fudge_dice(self, count: int = 4) -> Tuple[int, List[int]]:
        """Roll Fudge/FATE dice (-1, 0, +1)"""
        # Fudge die: 1-2 = -1, 3-4 = 0, 5-6 = +1
        rolls = []
        for _ in range(count):
            d6_roll = self.roll_d6()
            if d6_roll <= 2:
                rolls.append(-1)
            elif d6_roll <= 4:
                rolls.append(0)
            else:
                rolls.append(1)
        return sum(rolls), rolls

    # ----------------------------
    # Abstract Methods
    # ----------------------------
    @abstractmethod
    def determine_hit(
        self, roll: int, difficulty: int, action_type: str
    ) -> Tuple[bool, str]:
        """
        Determine if an action succeeds and what type of success/failure.
        Must be implemented by game-specific rollers.
        """
        pass

    @abstractmethod
    def get_primary_die_size(self) -> int:
        """Return the primary die size for this game system (20 for D&D, 6 for some others)"""
        pass

    @abstractmethod
    def roll_primary(self) -> int:
        """Roll the primary die for this game system"""
        pass

    def roll_action(self, difficulty: int, action_type: str, **modifiers) -> DiceResult:
        """
        Roll for an action and return standardized result.
        This is the main method games should call.
        """
        # Get the base roll (implementation-specific)
        raw_roll = self.get_action_roll(**modifiers)
        total = self.calculate_total(raw_roll, **modifiers)

        # Determine success and outcome type (game-specific)
        hit, outcome_type = self.determine_hit(total, difficulty, action_type)

        # Check for critical/fumble (game-specific)
        critical = self.is_critical(raw_roll, hit, action_type)
        fumble = self.is_fumble(raw_roll, hit, action_type)

        return DiceResult(
            raw_roll=raw_roll,
            total=total,
            hit=hit,
            outcome_type=outcome_type,
            critical=critical,
            fumble=fumble,
            metadata=modifiers,
        )

    # ----------------------------
    # Extensible Hook Methods
    # ----------------------------
    def get_action_roll(self, **modifiers) -> int | List[int]:
        """Get the raw dice roll for an action. Override for special rolling mechanics."""
        return self.roll_primary()

    def calculate_total(self, raw_roll: int | List[int], **modifiers) -> int:
        """Calculate final total from raw roll and modifiers. Override for complex calculations."""
        base = raw_roll if isinstance(raw_roll, int) else sum(raw_roll)
        return base + modifiers.get("modifier", 0)

    def is_critical(
        self, raw_roll: int | List[int], hit: bool, action_type: str
    ) -> bool:
        """Determine if this is a critical success. Override for game-specific rules."""
        return False  # Default: no criticals

    def is_fumble(self, raw_roll: int | List[int], hit: bool, action_type: str) -> bool:
        """Determine if this is a critical failure/fumble. Override for game-specific rules."""
        return False  # Default: no fumbles


# ----------------------------
# Game-Specific Implementations
# ----------------------------


class DnDDiceRoller(BaseDiceRoller):
    """D&D 5e specific dice rolling implementation"""

    def get_primary_die_size(self) -> int:
        return 20

    def roll_primary(self) -> int:
        return self.roll_d20()

    def determine_hit(
        self, roll: int, difficulty: int, action_type: str
    ) -> Tuple[bool, str]:
        """D&D success determination with damage types"""
        hit = roll >= difficulty

        if hit:
            if roll == 20:
                return True, (
                    DamageType.critical
                    if action_type in ["attack", "spell"]
                    else DamageType.outstanding_success
                )
            elif roll >= 18:
                return True, (
                    DamageType.wound
                    if action_type in ["attack", "spell"]
                    else DamageType.great_success
                )
            else:
                return True, (
                    DamageType.wound
                    if action_type in ["attack", "spell"]
                    else DamageType.success
                )
        else:
            return False, (
                DamageType.miss
                if action_type in ["attack", "spell"]
                else DamageType.failure
            )

    def is_critical(
        self, raw_roll: int | List[int], hit: bool, action_type: str
    ) -> bool:
        """D&D critical hit on natural 20"""
        if isinstance(raw_roll, list):
            return max(raw_roll) == 20 and action_type in ["attack", "spell"]
        return raw_roll == 20 and action_type in ["attack", "spell"]

    def is_fumble(self, raw_roll: int | List[int], hit: bool, action_type: str) -> bool:
        """D&D critical miss on natural 1"""
        if isinstance(raw_roll, list):
            return min(raw_roll) == 1 and not hit
        return raw_roll == 1 and not hit

    def get_action_roll(self, **modifiers) -> int:
        """Handle advantage/disadvantage for D&D"""
        if modifiers.get("advantage"):
            result, _ = self.roll_with_advantage(20)
            return result
        elif modifiers.get("disadvantage"):
            result, _ = self.roll_with_disadvantage(20)
            return result
        else:
            return self.roll_d20()


class CyberpunkDiceRoller(BaseDiceRoller):
    """Cyberpunk 2020/RED style dice rolling (d10 based)"""

    def get_primary_die_size(self) -> int:
        return 10

    def roll_primary(self) -> int:
        return self.roll_d10()

    def determine_hit(
        self, roll: int, difficulty: int, action_type: str
    ) -> Tuple[bool, str]:
        """Cyberpunk success levels"""
        if roll >= difficulty + 10:
            return True, "spectacular_success"
        elif roll >= difficulty + 5:
            return True, "great_success"
        elif roll >= difficulty:
            return True, "success"
        elif roll >= difficulty - 5:
            return False, "near_miss"
        else:
            return False, "failure"

    def get_action_roll(self, **modifiers) -> int:
        """Cyberpunk exploding d10s"""
        total, _ = self.roll_exploding(10)
        return total

    def is_critical(
        self, raw_roll: int | List[int], hit: bool, action_type: str
    ) -> bool:
        """Cyberpunk critical on exploding dice"""
        if isinstance(raw_roll, list):
            return len(raw_roll) > 1  # Exploded at least once
        return False

    def is_fumble(self, raw_roll: int | List[int], hit: bool, action_type: str) -> bool:
        """Cyberpunk fumble on 1 when failing badly"""
        if isinstance(raw_roll, list):
            return raw_roll[0] == 1 and not hit
        return raw_roll == 1 and not hit


class WhiteWolfDiceRoller(BaseDiceRoller):
    """World of Darkness / White Wolf dice pool system"""

    def __init__(self, difficulty: int = 6, **kwargs):
        super().__init__(**kwargs)
        self.default_difficulty = difficulty

    def get_primary_die_size(self) -> int:
        return 10

    def roll_primary(self) -> int:
        return self.roll_d10()

    def get_action_roll(self, **modifiers) -> List[int]:
        """White Wolf uses dice pools"""
        dice_pool = modifiers.get("dice_pool", 1)
        return self.roll_dice(dice_pool, 10)

    def calculate_total(self, raw_roll: List[int], **modifiers) -> int:
        """Count successes in White Wolf"""
        difficulty = modifiers.get("difficulty", self.default_difficulty)
        successes = sum(1 for roll in raw_roll if roll >= difficulty)

        # Handle 10s (usually explode or count double)
        tens = sum(1 for roll in raw_roll if roll == 10)
        successes += tens  # 10s count as two successes

        # Handle 1s (botches)
        ones = sum(1 for roll in raw_roll if roll == 1)
        if successes == 0 and ones > 0:
            return -ones  # Botch!

        return max(0, successes - ones)

    def determine_hit(
        self, roll: int, difficulty: int, action_type: str
    ) -> Tuple[bool, str]:
        """White Wolf success determination"""
        if roll < 0:
            return False, "botch"
        elif roll == 0:
            return False, "failure"
        elif roll >= 5:
            return True, "exceptional_success"
        elif roll >= 3:
            return True, "great_success"
        elif roll >= 1:
            return True, "success"
        else:
            return False, "failure"


class SavageWorldsDiceRoller(BaseDiceRoller):
    """Savage Worlds exploding dice system"""

    def get_primary_die_size(self) -> int:
        return 6  # Wild die

    def roll_primary(self) -> int:
        return self.roll_d6()

    def get_action_roll(self, **modifiers) -> List[int]:
        """Savage Worlds trait die + wild die"""
        trait_die = modifiers.get("trait_die", 6)

        # Roll trait die (exploding)
        trait_result, _ = self.roll_exploding(trait_die)

        # Roll wild die (always d6, exploding)
        wild_result, _ = self.roll_exploding(6)

        return [trait_result, wild_result]

    def calculate_total(self, raw_roll: List[int], **modifiers) -> int:
        """Take the higher of trait die or wild die"""
        return max(raw_roll)

    def determine_hit(
        self, roll: int, difficulty: int, action_type: str
    ) -> Tuple[bool, str]:
        """Savage Worlds target numbers"""
        if roll >= difficulty + 8:
            return True, "legendary_success"
        elif roll >= difficulty + 4:
            return True, "great_success"
        elif roll >= difficulty:
            return True, "success"
        else:
            return False, "failure"


class FateDiceRoller(BaseDiceRoller):
    """FATE/Fudge dice system"""

    def get_primary_die_size(self) -> int:
        return 6  # Fudge dice are based on d6

    def roll_primary(self) -> int:
        result, _ = self.roll_fudge_dice(4)
        return result

    def get_action_roll(self, **modifiers) -> List[int]:
        """FATE uses 4 fudge dice"""
        _, rolls = self.roll_fudge_dice(4)
        return rolls

    def calculate_total(self, raw_roll: List[int], **modifiers) -> int:
        """Sum fudge dice and add skill"""
        dice_total = sum(raw_roll)
        skill_level = modifiers.get("skill", 0)
        return dice_total + skill_level

    def determine_hit(
        self, roll: int, difficulty: int, action_type: str
    ) -> Tuple[bool, str]:
        """FATE success levels"""
        shift = roll - difficulty
        if shift >= 3:
            return True, "epic_success"
        elif shift >= 1:
            return True, "success"
        elif shift >= 0:
            return True, "tie"
        elif shift >= -2:
            return False, "failure"
        else:
            return False, "critical_failure"


# ----------------------------
# Factory for Game Engines
# ----------------------------


class DiceRollerFactory:
    """Factory to create appropriate dice rollers for different game systems"""

    _rollers = {
        "dnd": DnDDiceRoller,
        "cyberpunk": CyberpunkDiceRoller,
        "whitewolf": WhiteWolfDiceRoller,
        "savage_worlds": SavageWorldsDiceRoller,
        "fate": FateDiceRoller,
    }

    @classmethod
    def create_roller(cls, game_system: str, **kwargs) -> BaseDiceRoller:
        """Create a dice roller for the specified game system"""
        if game_system.lower() not in cls._rollers:
            raise ValueError(f"Unknown game system: {game_system}")

        roller_class = cls._rollers[game_system.lower()]
        return roller_class(**kwargs)

    @classmethod
    def register_roller(cls, game_system: str, roller_class: type):
        """Register a new dice roller for a game system"""
        cls._rollers[game_system.lower()] = roller_class
