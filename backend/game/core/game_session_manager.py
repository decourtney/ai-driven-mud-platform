import uuid
import json
from prisma import Json
from typing import Dict, Any, Optional
from backend.services.api.server import prisma
from backend.models import GameSessionCreate, GameSessionDelete
from backend.game.game_registry import GAME_REGISTRY
from backend.game.engine_registry import ENGINE_REGISTRY
from backend.services.ai_models.model_client import AsyncModelServiceClient
# from backend.game.core.game_state import GameState

class GameSessionManager:
    def __init__(self, model_client: AsyncModelServiceClient):
        self.model_client = model_client
        
    async def get_session_status(self, user_id: str, slug: str) -> Optional[str]:
        session = await prisma.gamesession.find_first(
            where={"user_id": user_id, "slug": slug}
        )
        return session.id if session else None

    async def create_session(self, request: GameSessionCreate) -> str:
        """Create a new game session and persist it to DB"""
        if request.slug not in GAME_REGISTRY:
            raise ValueError(f"Unknown game: {request.slug}")

        engine_name = GAME_REGISTRY[request.slug]["engine"]
        if engine_name not in ENGINE_REGISTRY:
            raise ValueError(f"Engine not registered: {engine_name}")
                
        engine_class = ENGINE_REGISTRY[engine_name]
        engine = engine_class(model_client=self.model_client)
        game_state = engine.create_game_state(request.player_state)
        
        print("DEBUG: Initialized Game State: ", game_state)
        print("USERID: ", request.user_id)
        
        session_id = str(uuid.uuid4())
        
        await prisma.gamesession.create(
            data={
                "id": session_id,
                "user_id": request.user_id,
                "slug": request.slug,
                "game_state": Json(game_state),
                "is_active": True
            }
        )
        
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a session from DB"""
        record = await prisma.gamesession.find_unique(where={"id": session_id})
        if not record:
            return None
        return {
            "id": record.id,
            "user_id": record.user_id,
            "slug": record.slug,
            "game_state": record.game_state,
            "is_active": record.is_active
        }

    async def update_session(self, session_id: str, data: Dict[str, Any]):
        """Update a session in DB"""
        await prisma.gamesession.update(
            where={"id": session_id},
            data={
                "game_state": data.get("game_state"),
                "is_active": data.get("is_active")
            }
        )

    async def delete_session(self, request: GameSessionDelete):
        session = await prisma.gamesession.find_first(
            where={"user_id": request.user_id, "slug": request.slug, "id": request.session_id}
        )
        if not session:
            raise ValueError("Session not found")
        await prisma.gamesession.delete(where={"id": request.session_id})


    async def list_active_sessions(self, user_id: Optional[str] = None):
        """List active sessions optionally filtered by user"""
        filters = {"isActive": True}
        if user_id:
            filters["userId"] = user_id

        records = await prisma.gamesession.find_many(where=filters)
        return [
            {
                "id": r.id,
                "user_id": r.user_id,
                "slug": r.slug,
                "is_active": r.is_active
            }
            for r in records
        ]
