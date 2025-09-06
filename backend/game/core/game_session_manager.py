import uuid
import json
from prisma import Json
from typing import Dict, Any, Optional
from fastapi import HTTPException
from backend.services.api.server import prisma
from backend.game.core.game_engine_manager import GameEngineManager
from backend.models import GameSessionResponse
from backend.game.game_registry import GAME_REGISTRY
from backend.game.engine_registry import ENGINE_REGISTRY
from backend.services.ai_models.model_client import AsyncModelServiceClient

# from backend.game.core.game_state import GameState


class GameSessionManager:
    def __init__(self, model_client: AsyncModelServiceClient):
        self.model_client = model_client
        self.engine_manager = GameEngineManager(cleanup_interval=60)

    # ==========================================
    # Engine Manager Cleanup Start/Stop
    # ==========================================
    async def start(self):
        await self.engine_manager.start()

    async def stop(self):
        await self.engine_manager.stop()

    # ==========================================
    # Session Status
    # ==========================================
    async def get_session_status(self, user_id: str, slug: str) -> Optional[str]:
        session = await prisma.gamesession.find_first(
            where={"user_id": user_id, "slug": slug}
        )
        return session.id if session else None

    # ==========================================
    # Session Management
    # ==========================================
    async def create_session(
        self,
        player_state: Dict[str, Any],
        slug: str,
        user_id: str,
    ):
        """Create a new game session and persist it to DB"""
        if slug not in GAME_REGISTRY:
            raise ValueError(f"Unknown game: {slug}")

        if not await self.model_client.is_healthy():
            raise HTTPException(
                status_code=503,
                detail=f"Model server not available at {self.model_client.base_url}",
            )

        # Delete existing session for this user/game if it exists
        await prisma.gamesession.delete_many(where={"user_id": user_id, "slug": slug})

        engine_name = GAME_REGISTRY[slug]["engine"]
        if engine_name not in ENGINE_REGISTRY:
            raise ValueError(f"Engine not registered: {engine_name}")

        # Create Game Engine Instance
        engine_class = ENGINE_REGISTRY[engine_name]
        engine = engine_class(model_client=self.model_client)

        # Reconstitute seralized player state into engine instance
        game_state = engine.create_game_state(player_state)

        # Create ID for new game session
        session_id = str(uuid.uuid4())

        # Register engine instance in memory
        engine_id = self.engine_manager.register_engine(
            engine, session_id=session_id, slug=slug
        )

        await prisma.gamesession.create(
            data={
                "id": session_id,
                "user_id": user_id,
                "slug": slug,
                "game_state": Json(game_state),
                "is_active": True,
            }
        )

        return {
            "session_id": session_id,
            "engine_id": engine_id,
        }

    async def get_session(self, slug: str, session_id: str, user_id: str):
        """Load a session from DB"""
        if not await self.model_client.is_healthy():
            raise HTTPException(
                status_code=503,
                detail=f"Model server not available at {self.model_client.base_url}",
            )

        record = await prisma.gamesession.find_unique(
            where={
                "user_id": user_id,
                "slug": slug,
                "id": session_id,
            }
        )
        if not record:
            raise HTTPException(
                status_code=503,
                detail=f"Couldn't locate this session.",
            )

        engine_name = GAME_REGISTRY[slug]["engine"]
        if engine_name not in ENGINE_REGISTRY:
            raise ValueError(f"Engine not registered: {engine_name}")

        # ==========================================
        # Return the existing engine if available
        # ==========================================
        existing_engine_id = self.engine_manager.get_registered_engine_id(slug, session_id)
        if existing_engine_id:
            return {
                "session_id": record.id,
                "engine_id": existing_engine_id,
            }

        # ==========================================
        # Else create a new instance
        # ==========================================
        engine_class = ENGINE_REGISTRY[engine_name]
        engine = engine_class(model_client=self.model_client)

        # Reconstitute seralized game state record into engine instance
        engine.load_game_state(record.game_state)

        # Register engine instance in memory
        engine_id = self.engine_manager.register_engine(
            engine, session_id=record.id, slug=record.slug
        )

        return {
            "session_id": record.id,
            "engine_id": engine_id,
        }

    async def update_session(self, session_id: str, data: Dict[str, Any]):
        """Update a session in DB"""
        await prisma.gamesession.update(
            where={"id": session_id},
            data={
                "game_state": data.get("game_state"),
                "is_active": data.get("is_active"),
            },
        )

    async def delete_session(self, slug: str, session_id: str, user_id: str):
        session = await prisma.gamesession.find_first(
            where={
                "user_id": user_id,
                "slug": slug,
                "id": session_id,
            }
        )
        if not session:
            raise ValueError("Session not found")
        await prisma.gamesession.delete(where={"id": session_id})

    async def list_active_sessions(self, user_id: Optional[str] = None):
        """List active sessions optionally filtered by user"""
        filters = {"isActive": True}
        if user_id:
            filters["userId"] = user_id

        records = await prisma.gamesession.find_many(where=filters)
        return [
            {"id": r.id, "user_id": r.user_id, "slug": r.slug, "is_active": r.is_active}
            for r in records
        ]

    async def list_registered_engines(self):
        """List all currently registered engine instances"""
        engine_instances = await self.engine_manager.list_registered_engines()

        if not engine_instances:
            raise ValueError("No instances found")
        return {"engine_instances": engine_instances}

    async def list_registered_engines_by_game(self, slug: str):
        engine_instances = await self.engine_manager.list_registered_engines_by_game(
            slug
        )
        if not engine_instances:
            raise ValueError("No instances found")
        return {"engine_instances": engine_instances}
