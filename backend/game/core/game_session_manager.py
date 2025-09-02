import uuid
from typing import Dict, Any, Optional
from backend.services.api.server import prisma
from backend.models import GameSessionCreate
from backend.game.game_registry import GAME_REGISTRY
from backend.game.engine_registry import ENGINE_REGISTRY

class GameSessionManager:
    def __init__(self):
        pass

    async def create_session(self, request: GameSessionCreate, user_id: str) -> str:
        """Create a new game session and persist it to DB"""
        if request.slug not in GAME_REGISTRY:
            raise ValueError(f"Unknown game: {request.slug}")

        engine_name = GAME_REGISTRY[request.slug]["engine"]
        if engine_name not in ENGINE_REGISTRY:
            raise ValueError(f"Engine not registered: {engine_name}")

        engine_class = ENGINE_REGISTRY[engine_name]
        engine = engine_class()
        state = engine.initialize_game(request.player_setup)

        session_id = str(uuid.uuid4())

        await prisma.gamesession.create(
            data={
                "id": session_id,
                "userId": user_id,
                "slug": request.slug,
                "playerSetup": request.player_setup,
                "sceneState": state,
                "turnNumber": 0,
                "isActive": True
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
            "user_id": record.userId,
            "slug": record.slug,
            "player_setup": record.playerSetup,
            "scene_state": record.sceneState,
            "turn_number": record.turnNumber,
            "is_active": record.isActive
        }

    async def update_session(self, session_id: str, data: Dict[str, Any]):
        """Update a session in DB"""
        await prisma.gamesession.update(
            where={"id": session_id},
            data={
                "sceneState": data.get("scene_state"),
                "turnNumber": data.get("turn_number"),
                "isActive": data.get("is_active")
            }
        )

    async def delete_session(self, session_id: str):
        """Delete a session from DB"""
        await prisma.gamesession.delete(where={"id": session_id})

    async def list_active_sessions(self, user_id: Optional[str] = None):
        """List active sessions optionally filtered by user"""
        filters = {"isActive": True}
        if user_id:
            filters["userId"] = user_id

        records = await prisma.gamesession.find_many(where=filters)
        return [
            {
                "id": r.id,
                "user_id": r.userId,
                "slug": r.slug,
                "turn_number": r.turnNumber,
                "is_active": r.isActive
            }
            for r in records
        ]
