from pydantic import BaseModel
from typing import List, Dict, Any

from backend.core.scenes.scene_models import Exit


class SceneExitResult(BaseModel):
    target_scene: str


class SceneExitRequest(BaseModel):
    target: str
    scene_exits: List[Exit]


class GenerateSceneRequest(BaseModel):
    scene: Dict[str, Any]
    player: Dict[str, Any]


class GeneratedNarration(BaseModel):
    # Reponse for any narration generation
    narration: str
