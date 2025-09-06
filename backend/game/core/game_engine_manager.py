import uuid
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta, timezone


class GameEngineManager:
    """
    Manage live game engine instances in memory.
    """

    def __init__(self, cleanup_interval: int = 60):
        # engine_id -> {"engine": EngineInstance, "session_id": str, "last_active": datetime}
        self.engines: Dict[str, dict] = {}
        self.engines_by_game: Dict[str, Dict[str, dict]] = {}
        self.cleanup_interval = cleanup_interval
        self._cleanup_task = None  # Store cleanup loop task

    async def start(self):
        """Start the cleanup loop."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self.cleanup_loop())

    async def stop(self):
        """Stop the cleanup loop and wait for task to finish."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def cleanup_loop(self):
        """Periodically remove idle engine instances."""
        while True:
            await asyncio.sleep(self.cleanup_interval)
            now = datetime.now(timezone.utc)
            idle_threshold = timedelta(minutes=30)  # configurable
            to_delete = [
                eid
                for eid, entry in self.engines_by_game.items()
                if now - entry["last_active"] > idle_threshold
            ]
            for eid in to_delete:
                del self.engines_by_game[eid]

    def register_engine(self, engine_instance, session_id: str, slug: str) -> str:
        """Register a new engine instance and return its engine_id."""
        engine_id = str(uuid.uuid4())
        if slug not in self.engines_by_game:
            self.engines_by_game[slug] = {}
        self.engines_by_game[slug][session_id] = {
            "engine": engine_instance,
            "engine_id": engine_id,
            "last_active": datetime.now(timezone.utc),
        }
        return engine_id


    def get_registered_engine_id(self, slug: str, session_id: str) -> str | None:
        entry = self.engines_by_game.get(slug, {}).get(session_id)
        if not entry:
            return None

        entry["last_active"] = datetime.now(timezone.utc)
        return entry["engine_id"]

    def unregister_engine(self, slug: str, session_id: str) -> bool:
        """Remove engine from memory."""
        if slug in self.engines_by_game and session_id in self.engines_by_game[slug]:
            del self.engines_by_game[slug][session_id]
            if not self.engines_by_game[slug]:
                del self.engines_by_game[slug]
            return True
        return False

    async def list_registered_engines(self):
        """Flat view: engine_id -> session_id"""
        flat = {}
        for slug_entries in self.engines_by_game.values():
            for session_id, entry in slug_entries.items():
                flat[entry["engine_id"]] = session_id
        return flat

    async def list_registered_engines_by_game(self, slug: str):
        """Return engine_id → session_id for a specific game slug."""
        slug_entries = self.engines_by_game.get(slug, {})
        return {
            entry["engine_id"]: session_id for session_id, entry in slug_entries.items()
        }

    # def register_engine(self, engine_instance, session_id: str, slug: str) -> str:
    #     """Register a new engine instance and return its engine_id."""
    #     engine_id = str(uuid.uuid4())
    #     print("[DEBUG] creating register for ", engine_id, session_id)
    #     self.engines[engine_id] = {
    #         "engine": engine_instance,
    #         "session_id": session_id,
    #         "slug": slug,
    #         "last_active": datetime.now(timezone.utc),
    #     }
    #     return engine_id

    # def get_registered_engine(self, engine_id: str):
    #     """Retrieve engine instance and update last_active."""
    #     entry = self.engines.get(engine_id)
    #     if not entry:
    #         raise ValueError(f"Engine {engine_id} not found")
    #     entry["last_active"] = datetime.now(timezone.utc)
    #     return entry["engine"]

    # def get_registered_engine_by_game_and_session(self, slug: str, session_id: str):
    #     """Retrieve engine instance by game slug and session_id, update last_active."""
    #     # Pre-filter engines by slug
    #     slug_engines = {
    #         eid: entry for eid, entry in self.engines.items() if entry["slug"] == slug
    #     }

    #     # Then search for the session_id
    #     for engine_id, entry in slug_engines.items():
    #         if entry["session_id"] == session_id:
    #             entry["last_active"] = datetime.now(timezone.utc)
    #             return entry["engine"], engine_id
    #     raise ValueError(
    #         f"No engine registered for game '{slug}' and session '{session_id}'"
    #     )
