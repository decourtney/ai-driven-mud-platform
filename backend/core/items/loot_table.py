from typing import List, Tuple
import random


class LootTable:
    """
    Simple loot table for NPCs or monsters.
    """

    def __init__(self, items: List[Tuple[str, float]]):
        """
        items: list of tuples (item_id, weight)
        """
        self.items = items
        self.total_weight = sum(weight for _, weight in items)

    def roll(self, count: int = 1) -> List[str]:
        """
        Return a list of item_ids based on weights.
        """
        if not self.items:
            return []

        results = []
        for _ in range(count):
            r = random.uniform(0, self.total_weight)
            upto = 0
            for item_id, weight in self.items:
                upto += weight
                if r <= upto:
                    results.append(item_id)
                    break
        return results
