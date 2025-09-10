import uuid
import json
from prisma import Json
from typing import Dict, Any, Optional, Callable
from fastapi import HTTPException
from backend.services.api.server import prisma
from backend.game.core.game_engine_manager import GameEngineManager
from backend.models import (
    ParseActionRequest,
    GenerateActionRequest,
    GeneratedNarration,
    GenerateSceneRequest,
)
from backend.game.game_registry import GAME_REGISTRY
from backend.game.engine_registry import ENGINE_REGISTRY
from backend.services.ai_models.model_client import AsyncModelServiceClient


class GameSessionManager:
    def __init__(self, model_client: AsyncModelServiceClient):
        self.model_client = model_client
        self.engine_manager = GameEngineManager(
            cleanup_interval=1, on_unregister=self.save_game_state
        )

    # ==========================================
    # Session Management
    # ==========================================

    async def query_session_status(self, user_id: str, slug: str) -> Optional[str]:
        session = await prisma.gamesession.find_first(
            where={"user_id": user_id, "slug": slug}
        )
        return session.id if session else None

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
        await self.delete_sessions(slug=slug, user_id=user_id)

        # Create engine instance
        engine_instance = self.engine_factory(slug=slug)

        # Reconstruct seralized player state into engine instance
        game_state = engine_instance.create_game_state(player_state)

        gamesession_record = await prisma.gamesession.create(
            data={
                "user_id": user_id,
                "slug": slug,
                "game_state": Json(game_state),
                "is_active": True,
            }
        )

        # Register engine instance in memory
        engine_id = self.engine_manager.register_engine(
            engine_instance, session_id=gamesession_record.id, slug=slug
        )

        ##############################################
        # NEED TO GENERATE INITIAL SCENE DESCRIPTION
        # WHEN INITIALIZING A NEW SESSION IN THE ENGINE
        ##############################################
        with open("backend/game/scenes/mudai/village.json", "r") as file:
            scene_conf = json.load(file)

        session_start_message = scene_conf

        scene_request = GenerateSceneRequest(
            scene=scene_conf["village_arrival"],
            player=game_state["player"],
        )

        initial_narration = await self.model_client.generate_scene(scene_request)

        await prisma.chatmessage.create_many(
            data=[
                {
                    "session_id": gamesession_record.id,
                    "speaker": "system",
                    "action": "narrate",
                    "content": session_start_message["session_start"]["description"],
                },
                {
                    "session_id": gamesession_record.id,
                    "speaker": "narrator",
                    "action": "narrate",
                    "content": initial_narration.narration,
                },
            ]
        )

        chatmessage_records = await prisma.chatmessage.find_many(
            where={"session_id": gamesession_record.id}
        )

        print("[DEBUG] Chat Message Records: ", chatmessage_records)

        # Remove unwanted fields from chatmessage
        chat_history = [self.serialize_chat_message(msg) for msg in chatmessage_records]

        return {
            "session_id": gamesession_record.id,
            "engine_id": engine_id,
            "game_state": game_state,
            "chat_history": chat_history,
        }

    async def get_session(self, slug: str, session_id: str, user_id: str):
        """Load a session from DB"""
        if not await self.model_client.is_healthy():
            raise HTTPException(
                status_code=503,
                detail=f"Model server not available at {self.model_client.base_url}",
            )

        gamesession_record = await prisma.gamesession.find_unique(
            where={
                "user_id": user_id,
                "slug": slug,
                "id": session_id,
            }
        )

        if not gamesession_record:
            raise HTTPException(
                status_code=503,
                detail=f"Couldn't locate this session.",
            )

        chatmessage_records = await prisma.chatmessage.find_many(
            where={"session_id": gamesession_record.id}
        )

        # Remove unwanted fields from chatmessage
        chat_history = [self.serialize_chat_message(msg) for msg in chatmessage_records]

        # ------------------------------------------
        # if available Return the existing engine
        # ------------------------------------------

        result = self.engine_manager.get_registered_engine(slug, session_id)

        if result:
            engine_id, engine = result
            game_state = engine.get_serialized_game_state()
            return {
                "session_id": gamesession_record.id,
                "engine_id": engine_id,
                "game_state": game_state,
                "chat_history": chat_history,
            }

        # ------------------------------------------
        # Else create a new instance
        # ------------------------------------------

        engine_instance = self.engine_factory(slug=slug)

        # Reconstitute seralized game state gamesession_record into engine instance
        game_state = engine_instance.load_serialized_game_state(
            gamesession_record.game_state
        )

        # Register engine instance in memory
        engine_id = self.engine_manager.register_engine(
            engine_instance,
            session_id=gamesession_record.id,
            slug=gamesession_record.slug,
        )

        return {
            "session_id": gamesession_record.id,
            "engine_id": engine_id,
            "game_state": game_state,
            "chat_history": chat_history,
        }

    async def delete_sessions(self, slug: str, user_id: str):
        sessions = await prisma.gamesession.find_many(
            where={"user_id": user_id, "slug": slug}
        )
        await prisma.gamesession.delete_many(where={"user_id": user_id, "slug": slug})

        for session in sessions:
            self.engine_manager.unregister_engine(
                slug=slug, session_id=session.id, serialize=False
            )

        return

    # ==========================================
    # GAME MANAGEMENT
    # ==========================================

    async def save_game_state(self, session_id: str, game_state: Dict[str, Any]):
        print("[DEBUG] SAVING GAME STATE TO DB")
        await prisma.gamesession.update(
            where={"id": session_id},
            data={"game_state": Json(game_state)},
        )
        return

    async def parse_action_request(
        self, session_id: str, action: ParseActionRequest
    ) -> GeneratedNarration:
        print("[DEBUG] Parse action requested")
        if not await self.model_client.is_healthy():
            raise HTTPException(status_code=503, detail="Model service not available")

        try:
            action_request = ParseActionRequest(action=action)
            parsed_action = await self.model_client.parse_action(action_request)
            print("[DEBUG] Parsed Action: ", parsed_action)

            generate_action_request = GenerateActionRequest(
                parsed_action=parsed_action, hit=True, damage_type="wound"
            )
            generated_action = await self.model_client.generate_action(
                generate_action_request
            )

            await prisma.chatmessage.create_many(
                data=[
                    {
                        "session_id": session_id,
                        "speaker": "player",
                        "action": "user_prompt",
                        "content": action,
                    },
                    {
                        "session_id": session_id,
                        "speaker": "narrator",
                        "action": parsed_action.action_type.value,
                        "content": generated_action.narration,
                    },
                ]
            )

            return generated_action
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Parse action failed: {str(e)}"
            )

    # ==========================================
    # ENGINE MANAGEMENT
    # ==========================================

    async def start(self):
        await self.engine_manager.start()

    async def stop(self):
        await self.engine_manager.stop()

    def engine_factory(self, slug: str):
        engine_name = GAME_REGISTRY[slug]["engine"]
        if engine_name not in ENGINE_REGISTRY:
            raise ValueError(f"Engine not registered: {engine_name}")

        # Create Game Engine Instance
        engine_class = ENGINE_REGISTRY[engine_name]
        engine = engine_class(
            model_client=self.model_client, save_state_callback=self.save_game_state
        )

        return engine

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
            return "No instances found"
        return {"engine_instances": engine_instances}

    # ==========================================
    # UTILS
    # ==========================================
    
    def serialize_chat_message(self, msg):
        return {
            "id": msg.id,
            "speaker": msg.speaker,
            "action": msg.action,
            "content": msg.content,
            "timestamp": msg.timestamp,
        }
