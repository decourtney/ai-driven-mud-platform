from typing import List, Optional, Dict
from pydantic import BaseModel
from enum import Enum


class QuestStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


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

    @classmethod
    def from_db(cls, record: dict):
        # Parse objectives JSON into ObjectiveState objects
        objectives = []
        raw_objectives = record.get("objectives") or []
        for obj in raw_objectives:
            if isinstance(obj, dict):
                objectives.append(ObjectiveState(**obj))
            else:
                # if Prisma returns JSON as string
                import json

                obj_data = json.loads(obj)
                objectives.append(ObjectiveState(**obj_data))

        return cls(
            quest_id=record["quest_id"],
            status=QuestStatus(record["status"]),
            objectives=objectives,
            started_at=record.get("created_at"),
            completed_at=record.get("completed_at"),
        )
