import json
import aiofiles
from pathlib import Path
from typing import Dict, Optional, Any
from backend.core.game_engine.event_bus import EventBus
from backend.core.characters.npc_library import NPC_LIBRARY
from backend.core.characters.npc_character import NpcCharacter
from backend.core.scenes.scene_models import (
    Scene,
    SceneDiff,
    Exit,
    Structure,
    SceneItem,
    Discovery,
    BlockedState,
    LockedState,
)


# -------------------------
# SceneManager
# -------------------------
class SceneManager:

    def __init__(self, scenemanager_root_path: Path, event_bus: EventBus):
        self.event_bus = event_bus
        self.scenemanager_root_path = scenemanager_root_path
        self.loaded_zone: Optional[str] = None
        self.loaded_scenes: Dict[str, Scene] = {}  # currently loaded scenes
        self.scene_diffs: Dict[str, SceneDiff] = {}  # track diffs per scene

    # -------------------------
    # zone loading/unloading
    # -------------------------
    async def load_zone(self, zone_name: str):
        if self.loaded_zone == zone_name:
            return  # already loaded

        self.unload_current_zone()  # unload previous

        file_path = self.scenemanager_root_path / f"{zone_name}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Zone {zone_name} not found at {file_path}")

        async with aiofiles.open(file_path) as f:
            contents = await f.read()
            data = json.loads(contents)

        self.loaded_scenes = {}
        for scene_id, scene_data in data.items():
            # Build Scene object
            scene = Scene(
                id=scene_data["id"],
                label=scene_data["label"],
                description=scene_data["description"],
                exits=[
                    Exit(
                        id=exit["id"],
                        label=exit["label"],
                        target_scene=exit["target_scene"],
                        blocked=BlockedState(**exit.get("blocked", {"active": False})),
                        locked=LockedState(**exit.get("locked", {"active": False})),
                    )
                    for exit in scene_data["exits"]
                ],
                structures=[
                    Structure(**struct) for struct in scene_data.get("structures", [])
                ],
                notable_npcs=[
                    NpcCharacter(**nnpc) for nnpc in scene_data.get("notable_npcs", [])
                ],
                npcs=[NpcCharacter(**npc) for npc in scene_data.get("npcs", [])],
                scene_items=[SceneItem(**item) for item in scene_data.get("items", [])],
                discoveries=[
                    Discovery(**disc) for disc in scene_data.get("discoveries", [])
                ],
            )

            # Store it keyed by scene_id
            self.loaded_scenes[scene_id] = scene
        print("[DEBUG] SCENE MANAGER LOADED WITH ZONES AND SCENES")
        return

    def unload_current_zone(self):
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

    async def get_scene(self, scene_id: str, zone: Optional[str] = None) -> Scene:
        if zone and self.loaded_zone != zone:
            await self.load_zone(zone)
        if scene_id not in self.loaded_scenes:
            raise KeyError(f"Scene {scene_id} not found in zone {zone}")

        base_scene = self.loaded_scenes[scene_id]
        scene_data = base_scene.model_dump()

        # Apply diffs if any
        if scene_id in self.scene_diffs:
            diff = self.scene_diffs[scene_id].changes
            scene_data = self.deep_merge(scene_data, diff)

        # Instantiate dynamic NPCs if none yet
        if not scene_data.get("npcs"):
            dynamic_npcs = []
            for npc_id in ["rabid_wolf"]:  # could pull from spawn tables later
                npc_template = NPC_LIBRARY[npc_id]
                print("",npc_template)
                dynamic_npcs.append(NpcCharacter(**npc_template))
            scene_data["npcs"] = dynamic_npcs

        return Scene(**scene_data)

    def move_to_scene(self, current_scene: Scene, exit_id: str) -> Scene:
        print("[DEBUG] Move to scene from", current_scene)
        print("[DEBUG] Exit id", exit_id)
        exit_ = next((e for e in current_scene.exits if e.id == exit_id), None)
        if not exit_:
            raise ValueError(f"Exit {exit_id} not found in scene {current_scene.id}")
        return self.get_scene(exit_.zone, exit_.target_scene)

    # -------------------------
    # Diff tracking
    # -------------------------

    async def emit_diff_update(self, scene_id: str, diff: Dict[str, Any]):
        if scene_id not in self.scene_diffs:
            self.scene_diffs[scene_id] = SceneDiff(scene_id=scene_id, changes={})

        self.scene_diffs[scene_id].changes = self.deep_merge(
            self.scene_diffs[scene_id].changes, diff
        )

        print(f"[SceneManager] Diff applied to {scene_id}: {diff}")
        await self.event_bus.emit("scene_changed", scene_id, diff)

    # NOTE: currently untested
    def deep_merge(self, base: dict, diff: dict) -> dict:
        """
        Merge diff into base.
        - Dicts are merged recursively.
        - Lists of dicts with 'id' are merged by matching 'id'.
        - Scalars or new keys overwrite base.
        """
        for key, value in diff.items():
            if key in base:
                if isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = self.deep_merge(base[key], value)
                elif isinstance(base[key], list) and isinstance(value, list):
                    # merge lists of dicts by 'id'
                    base[key] = self.merge_list_by_id(base[key], value)
                else:
                    base[key] = value
            else:
                base[key] = value
        return base

    @staticmethod
    def merge_list_by_id(base_list: list, diff_list: list) -> list:
        """
        Merge two lists of dicts, matching items by 'id'.
        If an item in diff_list has a matching id in base_list, recursively merge it.
        Otherwise, append the new item.
        """
        base_map = {
            item.get("id"): item
            for item in base_list
            if isinstance(item, dict) and "id" in item
        }
        for item in diff_list:
            if isinstance(item, dict) and "id" in item:
                if item["id"] in base_map:
                    base_map[item["id"]] = SceneManager.deep_merge(
                        base_map[item["id"]], item
                    )
                else:
                    base_map[item["id"]] = item
            else:
                # non-dict items or items without id just append
                base_list.append(item)
        return list(base_map.values())
