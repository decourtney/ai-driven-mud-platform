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
                        print("[DEBUG]Purging old engine instances")
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


    def get_registered_engine(
        self, game_id: str, session_id: str
    ) -> Optional[tuple[str, object]]:
        game_engines = self.engines.get(game_id)
        if not game_engines:
            return None

        entry = game_engines.get(session_id)
        if not entry:
            return None

        engine_id = entry.get("engine_id")
        engine = entry.get("engine")

        if not engine_id or not engine:
            # just return None, don't modify dicts
            return None

        # Refresh last_active timestamp
        entry["last_active"] = datetime.now(timezone.utc)

        return engine_id, engine

    def register_engine(
        self, engine_instance: object, session_id: str, game_id: str
    ) -> str:
        if not game_id or not session_id:
            raise ValueError("game_id and session_id are required to register an engine")

        if engine_instance is None:
            raise ValueError("engine_instance cannot be None")

        engine_id = str(uuid.uuid4())

        if game_id not in self.engines:
            self.engines[game_id] = {}

        # Overwrite old session entry if it exists
        self.engines[game_id][session_id] = {
            "engine": engine_instance,
            "engine_id": engine_id,
            "last_active": datetime.now(timezone.utc),
        }

        return engine_id

    async def unregister_engine(
        self, game_id: str, session_id: str, is_save: bool = True
    ) -> Optional[dict]:
        entry = self.engines.get(game_id, {}).pop(session_id, None)
        if not entry:
            return None

        engine = entry["engine"]
        engine_state = None

        if is_save:
            try:
                game_state, player_state = engine.get_serialized_game_state()
                await self.save_session(
                    session_id=session_id,
                    game_state=game_state,
                    player_state=player_state,
                )
            except Exception:
                import traceback

                print(f"[ERROR] Failed to save session {session_id} during unregister")
                traceback.print_exc()

        # clean up if no sessions left for this game_id
        if not self.engines.get(game_id):
            self.engines.pop(game_id, None)

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
