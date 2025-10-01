from pydantic import BaseModel
from typing import List, Dict, Any
from enum import Enum


class GameStatus(str, Enum):
    active = "active"
    maintenance = "maintenance"
    beta = "beta"


class GameDifficulty(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    parser_ready: bool
    narrator_ready: bool
    memory_usage: Dict[str, Any]
    uptime_seconds: float


class GameInfo(BaseModel):
    slug: str
    engine: str
    title: str
    description: str
    player_count: int
    status: GameStatus
    difficulty: GameDifficulty
    estimated_time: str
    features: List[str]
    thumbnail: str
    tags: List[str]


class GameSessionResponse(BaseModel):
    session_id: str
    engine_id: str
    game_state: Dict[str, Any]
