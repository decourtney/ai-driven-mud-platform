"""
FastAPI server for D&D Streaming Game Engine.
Now uses decoupled model service instead of direct model management.
"""

from fastapi import FastAPI, HTTPException, Query, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
import uuid
from datetime import datetime
from prisma import Prisma
from contextlib import asynccontextmanager

from backend.services.api.database import prisma
from backend.game.game_registry import GAME_REGISTRY
from backend.game.core.game_session_manager import GameSessionManager
from backend.game.core.character_state import CharacterState
from backend.services.ai_models.model_client import AsyncModelServiceClient
from backend.models import (
    GameInfo,
    GameSessionResponse,
    ParseActionRequest,
    GenerateActionRequest,
    GenerateSceneRequest,
    ParsedAction,
    ActionType,
)


class GameAPI:
    """Main game API server - now uses model service client"""

    def __init__(self, model_server_url: str = "http://localhost:8001", lifespan=None):
        self.model_client = AsyncModelServiceClient(model_server_url)
        self.session_manager = GameSessionManager(model_client=self.model_client)
        self.app = self._create_app(lifespan=lifespan)

    def _create_app(self, lifespan=None) -> FastAPI:
        """Create and configure FastAPI application"""
        app = FastAPI(
            title="D&D Streaming Game API",
            version="2.0.0",
            description="Real-time D&D game engine with decoupled AI models",
            lifespan=lifespan,
        )

        # Store server instance in app state for access in startup/shutdown events
        app.state.game_server = self

        # CORS middleware for Next.js development
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # ==========================================
        # Health & Status Endpoints
        # ==========================================

        @app.get("/health")
        async def health_check():
            """Health check endpoint with model service status"""
            model_status = await self.model_client.get_status()

            return {
                "status": "healthy",
                "api_server": "running",
                "model_service": {
                    "available": await self.model_client.is_healthy(),
                    "url": self.model_client.base_url,
                    "models_loaded": model_status.get("models", {}).get(
                        "all_loaded", False
                    ),
                    "parser_ready": model_status.get("models", {}).get(
                        "parser_loaded", False
                    ),
                    "narrator_ready": model_status.get("models", {}).get(
                        "narrator_loaded", False
                    ),
                },
            }

        @app.get("/{slug}/engines")
        async def list_engines(
            slug: str = Path(...),
        ):
            """List all registered engine instances by game"""
            try:
                instances = await self.session_manager.list_registered_engines_by_game(
                    slug=slug
                )

                return instances
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to get engines: {str(e)}"
                )

        @app.get("/sessions")
        async def list_sessions():
            """List all active sessions (for admin/debugging)"""
            return {
                "total_sessions": len(self.active_sessions),
                "sessions": [
                    {
                        "session_id": session.session_id,
                        "game_slug": session.game_slug,
                        "created_at": session.created_at.isoformat(),
                        "last_activity": session.last_activity.isoformat(),
                    }
                    for session in self.active_sessions.values()
                ],
            }

        # ==========================================
        # LOBBY ENDPOINTS
        # ==========================================

        @app.get("/lobby", response_model=list[GameInfo])
        def list_games():
            """Get list of available games"""
            return [
                GameInfo(
                    slug=slug,
                    engine=meta["engine"],
                    title=meta["title"],
                    description=meta["description"],
                    player_count=meta["player_count"],
                    status=meta["status"],
                    difficulty=meta["difficulty"],
                    estimated_time=meta["estimated_time"],
                    features=meta["features"],
                    thumbnail=meta["thumbnail"],
                    tags=meta["tags"],
                )
                for slug, meta in GAME_REGISTRY.items()
            ]

        @app.get("/lobby/{game_slug}")
        def get_game_details(game_slug: str):
            """Get detailed information about a specific game"""
            if game_slug not in GAME_REGISTRY:
                raise HTTPException(status_code=404, detail="Game not found")

            meta = GAME_REGISTRY[game_slug]
            return GameInfo(
                slug=game_slug,
                engine=meta["engine"],
                title=meta["title"],
                description=meta["description"],
                player_count=meta["player_count"],
                status=meta["status"],
                difficulty=meta["difficulty"],
                estimated_time=meta["estimated_time"],
                features=meta["features"],
                thumbnail=meta["thumbnail"],
                tags=meta["tags"],
            )

        # ==========================================
        # MAIN MENU ENDPOINTS
        # ==========================================

        @app.get("/play/{slug}/{user_id}")
        async def get_session_status(
            slug: str = Path(...),
            user_id: str = Path(...),
        ):
            try:
                session_id = await self.session_manager.get_session_status(
                    user_id=user_id, slug=slug
                )
                return {"session_id": session_id}
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to get status: {str(e)}"
                )

        @app.post("/play/{slug}/{user_id}")
        async def create_game_session(
            slug: str = Path(...),
            user_id: str = Path(...),
            player_state: Dict[str, Any] = Body(...),
        ):
            """Create a new game session"""
            if slug not in GAME_REGISTRY:
                raise HTTPException(status_code=404, detail="Game not found")

            try:
                session = await self.session_manager.create_session(
                    player_state=player_state, slug=slug, user_id=user_id
                )

                return {
                    "session_id": session["session_id"],
                    "engine_id": session["engine_id"],
                    "game_state": session["game_state"],
                }
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to create session: {str(e)}"
                )

        @app.delete("/play/{slug}/{user_id}")
        async def delete_session(
            slug: str = Path(...),
            user_id: str = Path(...),
        ):
            """Delete/end a game session"""
            try:
                await self.session_manager.delete_sessions(slug=slug, user_id=user_id)
                return {"success": True}
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to delete session: {str(e)}"
                )

        # ==========================================
        # PLAY SESSION ENDPOINTS
        # ==========================================

        @app.get("/play/{slug}/{session_id}/{user_id}")
        async def get_session(
            slug: str = Path(...),
            session_id: str = Path(...),
            user_id: str = Path(...),
        ):
            """Get session"""
            try:
                session = await self.session_manager.get_session(
                    slug=slug, session_id=session_id, user_id=user_id
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to get session: {str(e)}"
                )

            return {
                "session_id": session["session_id"],
                "engine_id": session["engine_id"],
                "game_state": session["game_state"]
            }
        
        @app.post("/play/{slug}/{session_id}/action/{user_id}")
        async def process_player_action(
            slug: str = Path(...),
            session_id: str = Path(...),
            user_id: str = Path(...),
            action: str = Body(...),
        ):
            try:

                print("Action received: ", action)

                return {"success": True, "session_id": session_id}

            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Action processing failed: {str(e)}"
                )

        # ==========================================
        # MODEL SERVICE PROXY ENDPOINTS
        # ==========================================

        @app.get("/models/status")
        async def get_model_status():
            """Get model service status (proxy endpoint)"""
            return await self.model_client.get_status()

        @app.post("/models/load")
        async def load_models():
            """Load models via model service"""
            try:
                success = await self.model_client.load_all_models()
                return {"success": success}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @app.post("/models/unload")
        async def unload_models():
            """Unload models via model service"""
            try:
                success = await self.model_client.unload_all_models()
                return {"success": success}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @app.post("/models/reload")
        async def reload_models():
            """Reload models via model service"""
            try:
                success = await self.model_client.reload_models()
                return {"success": success}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # ==========================================
        # TESTING ENDPOINTS
        # ==========================================

        @app.post("/test/parse_action")
        async def test_parse_action():
            """Test action parsing directly"""
            if not await self.model_client.is_healthy():
                raise HTTPException(
                    status_code=503, detail="Model service not available"
                )

            try:
                request = ParseActionRequest(
                    action="I swing my axe at the goblin with all my might"
                )

                result = await self.model_client.parse_action(request)

                return {"result": result.model_dump()}

            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Parse test failed: {str(e)}"
                )

        @app.post("/test/generate_action")
        async def test_generate_action():
            """Test action narration generation directly"""
            if not await self.model_client.is_healthy():
                raise HTTPException(
                    status_code=503, detail="Model service not available"
                )

            try:
                request = GenerateActionRequest(
                    parsed_action=ParsedAction(
                        actor="Player",
                        action="Slap",
                        target="Goblin",
                        action_type=ActionType.ATTACK,
                    ),
                    hit=True,
                    damage_type="wound",
                )
                result = await self.model_client.generate_action(request)

                return {"result": result.model_dump()}

            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Generation test failed: {str(e)}"
                )

        @app.post("/test/generate_scene")
        async def test_generate_scene():
            """Test action narration generation directly"""
            if not await self.model_client.is_healthy():
                raise HTTPException(
                    status_code=503, detail="Model service not available"
                )

            try:
                request = GenerateSceneRequest(
                    scene={
                        "name": "Dark Cave",
                        "description": "Old damp cavern with a small stream, glowing fungi, and bats lining the ceiling.",
                        "recent_events": [
                            "You just fought a goblin and an orc.",
                            "The goblin was slain moments ago.",
                            "The orc is badly injured but still hostile.",
                        ],
                    },
                    player={
                        "name": "Aragorn",
                        "class": "Fighter",
                        "inventory": ["sword", "shield"],
                        "health_status": "somewhat wounded",
                    },
                    npcs=[
                        {"name": "Goblin", "hostile": True, "health_status": "dead"},
                        {
                            "name": "Orc",
                            "hostile": True,
                            "health_status": "badly injured",
                        },
                    ],
                )
                result = await self.model_client.generate_scene(request)

                return {"result": result.model_dump()}

            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Generation test failed: {str(e)}"
                )

        return app


# ==========================================
# FACTORY FUNCTION
# ==========================================


def create_server(
    model_server_url: str = "http://localhost:8001", lifespan=None
) -> FastAPI:
    """Factory function to create configured FastAPI server with model service"""
    api = GameAPI(model_server_url=model_server_url, lifespan=lifespan)
    return api.app


# ==========================================
# DEVELOPMENT SERVER
# ==========================================

if __name__ == "__main__":
    import uvicorn

    app = create_server()
    print(
        f"""
🎮 D&D Game API Server (Decoupled)
===================================
- API Server: http://localhost:8000
- Model Service: http://localhost:8001 (separate process)
- API Docs: http://localhost:8000/docs

Make sure to start the model service first:
  python model_service.py --load-models
    """
    )

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
