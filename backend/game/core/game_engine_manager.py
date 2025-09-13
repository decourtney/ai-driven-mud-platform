import uuid
import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class GameEngineManager:
    """
    Manage live game engine instances in memory.
    """
    def __init__(self, cleanup_interval: int = 60, on_unregister=None):
        self.engines: Dict[str, Dict[str, dict]] = {}
        self.cleanup_interval = cleanup_interval
        self._cleanup_task = None  # Store cleanup loop task
        self.on_unregister = on_unregister

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
        while True:
            await asyncio.sleep(self.cleanup_interval)
            now = datetime.now(timezone.utc)
            idle_threshold = timedelta(milliseconds=5000)
            to_delete = []

            # Identify engines to cleanup
            for slug, sessions in self.engines.items():
                for session_id, entry in sessions.items():
                    if now - entry["last_active"] > idle_threshold:
                        game_state: Dict[str, Any] = entry[
                            "engine"
                        ].get_serialized_game_state()
                        to_delete.append((slug, session_id, game_state))

            # Prepare async tasks
            tasks = []
            for slug, session_id, game_state in to_delete:
                if self.on_unregister:
                    tasks.append(self.on_unregister(session_id, game_state))
                # Remove engine from memory immediately
                self.engines[slug].pop(session_id, None)
                if not self.engines[slug]:
                    del self.engines[slug]

            # Run saves concurrently
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        # Log but continue
                        print(f"[WARNING] Error saving engine state: {result}")

    def register_engine(self, engine_instance, session_id: str, slug: str) -> str:
        """Register a new engine instance and return its engine_id."""
        engine_id = str(uuid.uuid4())
        if slug not in self.engines:
            self.engines[slug] = {}
        self.engines[slug][session_id] = {
            "engine": engine_instance,
            "engine_id": engine_id,
            "last_active": datetime.now(timezone.utc),
        }
        return engine_id

    def get_registered_engine(self, slug: str, session_id: str):
        entry = self.engines.get(slug, {}).get(session_id)
        if not entry:
            return None

        entry["last_active"] = datetime.now(timezone.utc)
        return entry["engine_id"], entry["engine"]

    def unregister_engine(
        self, slug: str, session_id: str, serialize: bool = True
    ) -> Optional[dict]:
        entry = self.engines.get(slug, {}).pop(session_id, None)
        if not entry:
            return None

        engine_state = None
        if serialize:
            engine_state = entry[
                "engine"
            ].get_serialized_game_state()  # or await if async

        if not self.engines[slug]:
            del self.engines[slug]

        return engine_state

    async def list_registered_engines(self):
        """Flat view: engine_id -> session_id"""
        flat = {}
        for slug_entries in self.engines.values():
            for session_id, entry in slug_entries.items():
                flat[entry["engine_id"]] = session_id
        return flat

    async def list_registered_engines_by_game(self, slug: str):
        """Return engine_id → session_id for a specific game slug."""
        slug_entries = self.engines.get(slug, {})
        return {
            entry["engine_id"]: session_id for session_id, entry in slug_entries.items()
        }
