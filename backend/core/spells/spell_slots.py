from pydantic import BaseModel, Field, field_validator
from typing import Dict


class SpellSlots(BaseModel):
    """Tracks current and maximum spell slots per level, Pydantic v2 style."""

    max_slots: Dict[int, int] = Field(default_factory=dict)
    current_slots: Dict[int, int] = Field(default_factory=dict)

    @field_validator("current_slots", mode="before")
    def init_current_slots(cls, v, info):
        """Initialize current_slots to match max_slots if not provided"""
        if not v:
            max_slots = info.data.get("max_slots", {})
            return max_slots.copy()
        return v

    def use_slot(self, level: int) -> bool:
        available_levels = sorted(
            [l for l in self.current_slots if l >= level and self.current_slots[l] > 0]
        )
        if not available_levels:
            return False
        chosen_level = available_levels[0]
        self.current_slots[chosen_level] -= 1
        return True

    def restore_slot(self, level: int):
        if level in self.max_slots:
            self.current_slots[level] = min(
                self.current_slots.get(level, 0) + 1, self.max_slots[level]
            )

    def restore_all(self):
        self.current_slots = self.max_slots.copy()

    @classmethod
    def from_db(cls, records: list[dict]) -> "SpellSlots":
        max_slots: dict[int, int] = {}
        current_slots: dict[int, int] = {}

        for r in records:
            lvl = r["level"]
            max_slots[lvl] = max_slots.get(lvl, 0) + 1
            if not r["used"]:
                current_slots[lvl] = current_slots.get(lvl, 0) + 1

        return cls(max_slots=max_slots, current_slots=current_slots)
