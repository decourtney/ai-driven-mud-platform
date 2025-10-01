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
    is_completed: bool = False


class QuestReward(BaseModel):
    gold: int = 0
    item_ids: List[str] = []
    xp: int = 0


class QuestDefinition(BaseModel):
    """Immutable definition of a quest"""

    id: str
    name: str
    description: str
    objectives: List[Objective]
    rewards: QuestReward


class QuestState(BaseModel):
    """Per-player quest progress"""

    quest_id: str
    status: QuestStatus = QuestStatus.NOT_STARTED
    completed_objectives: List[int] = []
