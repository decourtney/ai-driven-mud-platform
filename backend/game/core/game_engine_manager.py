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

    def __init__(self, cleanup_interval: int = 60, save_session=None):
        self.engines: Dict[str, Dict[str, dict]] = {}
        self.cleanup_interval = cleanup_interval
        self._cleanup_task = None  # Store cleanup loop task
        self.save_session = save_session

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
            for game_id, sessions in self.engines.items():
                for session_id, entry in sessions.items():
                    if now - entry["last_active"] > idle_threshold:
                        game_state, player_state = entry[
                            "engine"
                        ].get_serialized_game_state()
                        to_delete.append(
                            (session_id, game_id, game_state, player_state)
                        )

            # Prepare async tasks
            tasks = []
            for session_id, game_id, game_state, player_state in to_delete:
                if self.save_session:
                    tasks.append(
                        self.save_session(
                            session_id=session_id,
                            game_state=game_state,
                            player_state=player_state,
                        )
                    )
                # Remove engine from memory immediately
                self.engines[game_id].pop(session_id, None)
                if not self.engines[game_id]:
                    del self.engines[game_id]

            # Run saves concurrently
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        # Log but continue
                        print(f"[WARNING] Error saving engine state: {result}")

    def register_engine(self, engine_instance, session_id: str, game_id: str) -> str:
        """Register a new engine instance and return its engine_id."""
        engine_id = str(uuid.uuid4())
        if game_id not in self.engines:
            self.engines[game_id] = {}
        self.engines[game_id][session_id] = {
            "engine": engine_instance,
            "engine_id": engine_id,
            "last_active": datetime.now(timezone.utc),
        }
        return engine_id

    def get_registered_engine(self, game_id: str, session_id: str):
        entry = self.engines.get(game_id, {}).get(session_id)
        if not entry:
            return None

        entry["last_active"] = datetime.now(timezone.utc)
        return entry["engine_id"], entry["engine"]

    async def unregister_engine(
        self, game_id: str, session_id: str, is_save: bool = True
    ) -> Optional[dict]:
        entry = self.engines.get(game_id, {}).pop(session_id, None)
        if not entry:
            return None

        engine_state = None
        if is_save:
            game_state, player_state = entry["engine"].get_serialized_game_state()

        await self.save_session(
            session_id=session_id,
            game_state=game_state,
            player_state=player_state,
        )

        if not self.engines[game_id]:
            del self.engines[game_id]

        return engine_state

    async def list_registered_engines(self):
        """Flat view: engine_id -> session_id"""
        flat = {}
        for game_id_entries in self.engines.values():
            for session_id, entry in game_id_entries.items():
                flat[entry["engine_id"]] = session_id
        return flat

    async def list_registered_engines_by_game(self, game_id: str):
        """Return engine_id → session_id for a specific game game_id."""
        game_id_entries = self.engines.get(game_id, {})
        return {
            entry["engine_id"]: session_id
            for session_id, entry in game_id_entries.items()
        }
