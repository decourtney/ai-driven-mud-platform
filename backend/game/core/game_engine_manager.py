import uuid
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta, timezone


class GameEngineManager:
    """
    Manage live game engine instances in memory.
    """

    def __init__(self, cleanup_interval: int = 60):
        # Maps engine_id -> {"engine": EngineInstance, "session_id": str, "last_active": datetime}
        self.engines: Dict[str, dict] = {}
        self.cleanup_interval = cleanup_interval
        # Start background task for cleanup
        asyncio.create_task(self._cleanup_loop())

    def register_engine(self, engine_instance, session_id: str) -> str:
        """Register a new engine instance and return its engine_id."""
        engine_id = str(uuid.uuid4())
        self.engines[engine_id] = {
            "engine": engine_instance,
            "session_id": session_id,
            "last_active": datetime.now(timezone.utc),
        }
        return engine_id

    def get_registered_engine(self, engine_id: str):
        """Retrieve engine instance and update last_active."""
        entry = self.engines.get(engine_id)
        if not entry:
            raise ValueError(f"Engine {engine_id} not found")
        entry["last_active"] = datetime.now(timezone.utc)
        return entry["engine"]

    def unregister_engine(self, engine_id: str):
        """Remove engine from memory."""
        if engine_id in self.engines:
            del self.engines[engine_id]

    async def _cleanup_loop(self):
        """Periodically remove idle engine instances."""
        while True:
            await asyncio.sleep(self.cleanup_interval)
            now = datetime.now(timezone.utc)
            idle_threshold = timedelta(minutes=30)  # adjust as needed
            to_delete = [
                eid
                for eid, entry in self.engines.items()
                if now - entry["last_active"] > idle_threshold
            ]
            for eid in to_delete:
                del self.engines[eid]

    def list_registered_engines(self):
        """Optional: for debugging."""
        return {eid: entry["session_id"] for eid, entry in self.engines.items()}
