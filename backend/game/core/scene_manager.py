import json
from pathlib import Path
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from backend.game.core.event_bus import EventBus


# -------------------------
# Scene and Exit structures
# -------------------------
@dataclass
class Exit:
    id: str
    label: str
    target_scene: str
    is_locked: Optional[bool] = None
    zone: Optional[str] = None


@dataclass
class Scene:
    id: str
    title: str
    description: str
    exits: list[Exit] = field(default_factory=list)
    objects: dict = field(default_factory=dict)


@dataclass
class SceneDiff:
    scene_id: str
    changes: dict = field(default_factory=dict)


# -------------------------
# SceneManager
# -------------------------
class SceneManager:

    def __init__(self, scenemanager_root_path: Path, event_bus: EventBus):
        self.event_bus = event_bus
        self.scenemanager_root_path = scenemanager_root_path
        self.loaded_zone: Optional[str] = None
        self.loaded_scenes: Dict[str, Scene] = {}  # currently loaded zone
        self.scene_diffs: Dict[str, SceneDiff] = {}  # track diffs per scene

    # -------------------------
    # zone loading/unloading
    # -------------------------
    async def load_zone(self, zone_name: str):
        if self.loaded_zone == zone_name:
            return  # already loaded

        self._unload_current_zone()  # unload previous

        file_path = self.scenemanager_root_path / f"{zone_name}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Zone {zone_name} not found at {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.loaded_scenes = {}
        for scene_id, scene_data in data.items():
            # Build exits
            exits = [Exit(**exit_data) for exit_data in scene_data.get("exits", [])]

            # Build Scene object
            scene = Scene(
                id=scene_data["id"],
                title=scene_data.get("title", ""),
                description=scene_data.get("description", ""),
                exits=exits,
                objects={
                    "structures": scene_data.get("structures", []),
                    "npcs": scene_data.get("npcs", []),
                    "items": scene_data.get("items", []),
                    "discoveries": scene_data.get("discoveries", []),
                },
            )

            # Store it keyed by scene_id
            self.loaded_scenes[scene_id] = scene
        print("[DEBUG] LOADED ZONE AND SCENES")

    def _unload_current_zone(self):
        if self.loaded_zone and self.persist_callback:
            # Persist diffs before unloading
            for scene_id, diff in self.scene_diffs.items():
                # save diff
                pass
        self.loaded_scenes.clear()
        self.loaded_zone = None

    # -------------------------
    # Scene retrieval & navigation
    # -------------------------
    def get_scene(self, zone: str, scene_id: str) -> Scene:
        if self.loaded_zone != zone:
            self.load_zone(zone)
        if scene_id not in self.loaded_scenes:
            raise KeyError(f"Scene {scene_id} not found in zone {zone}")
        return self.loaded_scenes[scene_id]

    def move_to_scene(self, current_scene: Scene, exit_id: str) -> Scene:
        exit_ = next((e for e in current_scene.exits if e.id == exit_id), None)
        if not exit_:
            raise ValueError(f"Exit {exit_id} not found in scene {current_scene.id}")
        return self.get_scene(exit_.zone, exit_.target_scene)

    # -------------------------
    # Diff tracking
    # -------------------------
    async def emit_diff_update(self, scene_id: str, diff: Dict[str, Any]):
        # apply diff locally
        self.loaded_scenes[scene_id]["diffs"].append(diff)
        print(f"[SceneManager] Diff applied to {scene_id}: {diff}")

        # emit event to engine
        await self.event_bus.emit("scene_changed", scene_id, diff)
