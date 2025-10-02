from typing import List, Optional
from pydantic import BaseModel
from enum import Enum


class QuestStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Objective(BaseModel):
    description: str
    required: int = 1  # e.g., 10 wolves to kill


class ObjectiveState(BaseModel):
    index: int
    is_completed: bool = False
    progress: int = 0
    required: int = 1  # e.g., 10 wolves to kill


class QuestReward(BaseModel):
    gold: int = 0
    item_ids: List[str] = []
    xp: int = 0


class QuestDefinition(BaseModel):
    """Immutable quest template (shared for all players)."""
    id: str
    name: str
    description: str
    objectives: List[Objective]
    rewards: QuestReward
    prerequisites: List[str] = []
    level_requirement: int = 0
    quest_type: str = "side"  # later: Enum
    repeatable: bool = False


class QuestState(BaseModel):
    """Per-player quest progress."""
    quest_id: str
    status: QuestStatus = QuestStatus.NOT_STARTED
    objectives: List[ObjectiveState] = []
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
