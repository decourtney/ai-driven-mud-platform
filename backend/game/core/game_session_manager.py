import uuid
import json
import asyncio
import logging
from prisma import Json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from fastapi import HTTPException
from backend.services.api.server import prisma
from backend.game.core.game_engine_manager import GameEngineManager
from backend.models import (
    ParseActionRequest,
    GenerateActionRequest,
    GeneratedNarration,
    GenerateSceneRequest,
)
from backend.services.api.connection_manager import (
    ConnectionManager,
    WebSocketMessage,
)
from backend.game.game_registry import GAME_REGISTRY
from backend.game.engine_registry import ENGINE_REGISTRY
from backend.services.ai_models.model_client import AsyncModelServiceClient
from backend.services.api.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class GameSessionManager:

    def __init__(
        self,
        model_client: AsyncModelServiceClient,
        connection_manager: ConnectionManager,
    ):
        self.model_client = model_client
        self.connection_manager = connection_manager
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

    # Deletes any existing sessions and creates a new session for the user
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

        # Reconstruct serialized player state into engine instance
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

        return {
            "session_id": gamesession_record.id,
        }

    # Get an existing sessions data
    async def get_session(self, slug: str, session_id: str, user_id: str):
        """Load a session from DB - simplified since engine check is now elsewhere"""

        if not await self.model_client.is_healthy():
            raise HTTPException(
                status_code=503,
                detail=f"Model server not available at {self.model_client.base_url}",
            )

        gamesession_record = await prisma.gamesession.find_unique(
            where={"id": session_id}
        )
        if not gamesession_record:
            raise HTTPException(
                status_code=404,
                detail=f"Couldn't locate session {session_id}",
            )

        # Get chat history
        chatmessage_records = await prisma.chatmessage.find_many(
            where={"session_id": gamesession_record.id}
        )
        chat_history = [self.serialize_chat_message(msg) for msg in chatmessage_records]
        needs_initial_narration = len(chat_history) == 0

        # Ensure engine exists and get it directly
        engine_id, engine = await self.ensure_engine_exists(slug, session_id)

        game_state = engine.get_serialized_game_state()

        # Send initial state to WebSocket clients
        if hasattr(self, "connection_manager"):
            await self.connection_manager.send_to_session(
                session_id,
                WebSocketMessage.initial_state(
                    game_state=game_state, 
                    chat_history=chat_history
                ),
            )

        # Handle initial narration for new sessions
        if needs_initial_narration:
            asyncio.create_task(
                self.generate_initial_narration_for_session(
                    session_id=session_id, slug=slug
                )
            )

        return game_state

        # return {
        #     "game_state": game_state,
        #     "chat_history": chat_history,
        # }

    # async def get_session(self, slug: str, session_id: str, user_id: str):
    #     """Load a session from DB"""
    #     if not await self.model_client.is_healthy():
    #         raise HTTPException(
    #             status_code=503,
    #             detail=f"Model server not available at {self.model_client.base_url}",
    #         )

    #     gamesession_record = await prisma.gamesession.find_unique(
    #         where={
    #             "user_id": user_id,
    #             "slug": slug,
    #             "id": session_id,
    #         }
    #     )

    #     if not gamesession_record:
    #         raise HTTPException(
    #             status_code=503,
    #             detail=f"Couldn't locate this session.",
    #         )

    #     chatmessage_records = await prisma.chatmessage.find_many(
    #         where={"session_id": gamesession_record.id}
    #     )

    #     # Remove unwanted fields from chatmessage
    #     chat_history = [self.serialize_chat_message(msg) for msg in chatmessage_records]

    #     # ------------------------------------------
    #     # if available Return the existing engine
    #     # ------------------------------------------

    #     result = self.engine_manager.get_registered_engine(slug, session_id)

    #     if result:
    #         engine_id, engine = result
    #         game_state = engine.get_serialized_game_state()
    #         return {
    #             "session_id": gamesession_record.id,
    #             "engine_id": engine_id,
    #             "game_state": game_state,
    #             "chat_history": chat_history,
    #         }

    #     # ------------------------------------------
    #     # Else create a new instance
    #     # ------------------------------------------

    #     engine_instance = self.engine_factory(slug=slug)

    #     # Reconstitute seralized game state gamesession_record into engine instance
    #     game_state = engine_instance.load_serialized_game_state(
    #         gamesession_record.game_state
    #     )

    #     # Register engine instance in memory
    #     engine_id = self.engine_manager.register_engine(
    #         engine_instance,
    #         session_id=gamesession_record.id,
    #         slug=gamesession_record.slug,
    #     )

    #     return {
    #         "session_id": gamesession_record.id,
    #         "engine_id": engine_id,
    #         "game_state": game_state,
    #         "chat_history": chat_history,
    #     }

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

    async def parse_action_request(self, session_id: str, action: str, slug: str):
        """Process player action and send results via WebSocket"""
        try:
            # Ensure engine is loaded and get it directly
            engine_id, engine = await self.ensure_engine_exists(slug, session_id)
            logger.info(f"Engine {engine_id} ready for session {session_id}")

            # Send immediate acknowledgment
            if hasattr(self, "connection_manager"):
                await self.connection_manager.send_to_session(
                    session_id,
                    WebSocketMessage.action_received(action=action)
                )

            # Save the action as a chatmessage
            action_record = await prisma.chatmessage.create(
                {
                    "session_id": session_id,
                    "speaker": "player",
                    "action": "user_prompt", 
                    "content": action,
                },
            )

            # Send the action as a chat message first (immediate feedback)
            if hasattr(self, "connection_manager"):
                await self.connection_manager.send_to_session(
                    session_id,
                    WebSocketMessage.chat_message(
                        id=action_record.id,
                        speaker=action_record.speaker,
                        content=action_record.content,
                        timestamp=action_record.timestamp.isoformat(),
                    ),
                )

            # Parse action into structure json
            action_request = ParseActionRequest(action=action)
            parsed_action = await self.model_client.parse_action(action_request)
            print("[DEBUG] Parsed Action: ", parsed_action)

            # TODO: Future engine operations will go here
            # Based on parsed_action.action_type, perform engine operations:
            #
            # if parsed_action.action_type == ActionType.ATTACK:
            #     result = engine.process_attack(parsed_action)
            # elif parsed_action.action_type == ActionType.MOVE:
            #     result = engine.process_movement(parsed_action)
            # elif parsed_action.action_type == ActionType.CAST_SPELL:
            #     result = engine.process_spell(parsed_action)
            # etc.

            # Generate a narration of the action
            generate_action_request = GenerateActionRequest(
                parsed_action=parsed_action, hit=True, damage_type="wound"
            )
            generated_action = await self.model_client.generate_action(
                generate_action_request
            )

            # TODO: After engine operations are added, save updated game state
            # await self.save_game_state(session_id, engine.get_serialized_game_state())

            # Save action narration as chatmessage
            generated_result = await prisma.chatmessage.create(
                {
                    "session_id": session_id,
                    "speaker": "narrator",
                    "action": parsed_action.action_type.value,
                    "content": generated_action.narration,
                },
            )

            # Send narration as a chat message
            if hasattr(self, "connection_manager"):
                await self.connection_manager.send_to_session(
                    session_id,
                    WebSocketMessage.chat_message(
                        id=generated_result.id,
                        speaker=generated_result.speaker,
                        content=generated_result.content,
                        timestamp=generated_result.timestamp.isoformat(),
                    ),
                )

                # TODO: Send game state updates when engine operations are added
                # await self.connection_manager.send_to_session(
                #     session_id,
                #     WebSocketMessage.game_state_update(
                #         updates=engine.get_serialized_game_state()
                #     )
                # )

            # Return success status
            return {"success": True}

        except Exception as e:
            logger.error(f"Action processing failed: {e}")
            # Send error to WebSocket clients
            if hasattr(self, "connection_manager"):
                await self.connection_manager.send_to_session(
                    session_id,
                    WebSocketMessage.error(f"Action processing failed: {str(e)}")
                )
            raise

        except Exception as e:
            # Send error via WebSocket
            error_message = {
                "type": "error",
                "data": {
                    "message": f"Action processing failed: {str(e)}",
                    "error_code": "ACTION_FAILED",
                },
                "timestamp": datetime.now().isoformat(),
            }

            if hasattr(self, "connection_manager"):
                await self.connection_manager.send_to_session(
                    session_id,
                    WebSocketMessage.error(
                        message=f"Action processing failed: {str(e)}",
                        error_code="ACTION_FAILED",
                    ),
                )
            return {"success": False, "error": str(e)}

    # async def parse_action_request(
    #     self, session_id: str, action: ParseActionRequest
    # ) -> GeneratedNarration:
    #     print("[DEBUG] Parse action requested")
    #     if not await self.model_client.is_healthy():
    #         raise HTTPException(status_code=503, detail="Model service not available")

    #     try:
    #         action_request = ParseActionRequest(action=action)
    #         parsed_action = await self.model_client.parse_action(action_request)
    #         print("[DEBUG] Parsed Action: ", parsed_action)

    #         generate_action_request = GenerateActionRequest(
    #             parsed_action=parsed_action, hit=True, damage_type="wound"
    #         )
    #         generated_action = await self.model_client.generate_action(
    #             generate_action_request
    #         )

    #         await prisma.chatmessage.create_many(
    #             data=[
    #                 {
    #                     "session_id": session_id,
    #                     "speaker": "player",
    #                     "action": "user_prompt",
    #                     "content": action,
    #                 },
    #                 {
    #                     "session_id": session_id,
    #                     "speaker": "narrator",
    #                     "action": parsed_action.action_type.value,
    #                     "content": generated_action.narration,
    #                 },
    #             ]
    #         )

    #         return generated_action
    #     except Exception as e:
    #         raise HTTPException(
    #             status_code=500, detail=f"Parse action failed: {str(e)}"
    #         )

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
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
        }

    async def generate_initial_narration_for_session(self, session_id: str, slug: str):
        """Generate initial narration and send via WebSocket"""
        try:
            # Get session data
            gamesession_record = await prisma.gamesession.find_unique(
                where={"id": session_id}
            )

            if not gamesession_record:
                return

            # Load scene configuration
            with open(f"backend/game/scenes/{slug}/village.json", "r") as file:
                scene_conf = json.load(file)

            # Create system message first
            system_message = await prisma.chatmessage.create(
                data={
                    "session_id": session_id,
                    "speaker": "system",
                    "action": "narrate",
                    "content": scene_conf["session_start"]["description"],
                }
            )

            # Send system message via WebSocket immediately
            if hasattr(self, "connection_manager"):
                await self.connection_manager.send_to_session(
                    session_id,
                    WebSocketMessage.chat_message(
                        id=system_message.id,
                        speaker=system_message.speaker,
                        content=system_message.content,
                        timestamp=system_message.timestamp.isoformat(),
                    ),
                )

            # Generate AI narration
            scene_request = GenerateSceneRequest(
                scene=scene_conf["village_arrival"],
                player=gamesession_record.game_state["player"],
            )

            initial_narration = await self.model_client.generate_scene(scene_request)

            # Save AI narration to database
            narrator_message = await prisma.chatmessage.create(
                data={
                    "session_id": session_id,
                    "speaker": "narrator",
                    "action": "narrate",
                    "content": initial_narration.narration,
                }
            )

            # Send AI narration via WebSocket
            if hasattr(self, "connection_manager"):
                await self.connection_manager.send_to_session(
                    session_id,
                    WebSocketMessage.chat_message(
                        id=narrator_message.id,
                        speaker=narrator_message.speaker,
                        content=narrator_message.content,
                        timestamp=narrator_message.timestamp.isoformat(),
                    ),
                )

            print(f"[DEBUG] Generated initial narration for session {session_id}")

        except Exception as e:
            print(f"[ERROR] Failed to generate initial narration: {e}")
            # Send fallback message
            if hasattr(self, "connection_manager"):
                await self.connection_manager.send_to_session(
                    session_id,
                    WebSocketMessage.chat_message(
                        id=str(uuid.uuid4()),
                        speaker="system",
                        content="Welcome to your adventure! The world awaits your actions.",
                        timestamp=datetime.now().isoformat(),
                    ),
                )

    async def ensure_engine_exists(self, slug: str, session_id: str) -> Tuple[str, Any]:
        """
        Ensure an engine exists for the session, creating one if needed.
        Returns tuple of (engine_id, engine_instance).
        """
        # Check if engine is already registered and active
        result = self.engine_manager.get_registered_engine(slug, session_id)
        if result:
            engine_id, engine = result
            logger.info(f"Using existing engine {engine_id} for session {session_id}")
            return engine_id, engine

        # No engine exists (expired or first time), create new one
        logger.info(f"Creating new engine for session {session_id}")

        # Load session data from database
        gamesession_record = await prisma.gamesession.find_unique(where={"id": session_id})
        if not gamesession_record:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Create and initialize engine
        engine_instance = self.engine_factory(slug=slug)
        engine_instance.load_serialized_game_state(gamesession_record.game_state)

        # Register the new engine
        engine_id = self.engine_manager.register_engine(
            engine_instance,
            session_id=gamesession_record.id,
            slug=gamesession_record.slug,
        )

        logger.info(f"Registered new engine {engine_id} for session {session_id}")
        return engine_id, engine_instance
