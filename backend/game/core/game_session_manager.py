import uuid
import json
import asyncio
import logging
from prisma import Json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from fastapi import HTTPException
from backend.services.api.server import prisma
from backend.models import GenerateSceneRequest, CharacterType
from backend.services.api.connection_manager import (
    ConnectionManager,
    WebSocketMessage,
)
from backend.game.game_registry import GAME_REGISTRY
from backend.game.core.game_state import GameState, CharacterState

# from backend.game.engine_registry import ENGINE_REGISTRY
from backend.services.ai_models.model_client import AsyncModelServiceClient
from backend.game.core.game_engine_manager import GameEngineManager
from backend.game.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class GameSessionManager:

    def __init__(
        self,
        model_client: AsyncModelServiceClient,
        connection_manager: ConnectionManager,
        event_bus: EventBus,
    ):
        self.event_bus = event_bus
        self.model_client = model_client
        self.connection_manager = connection_manager
        self.engine_manager = GameEngineManager(
            cleanup_interval=1, save_session=self.save_session
        )

    # ==========================================
    # Session Management
    # ==========================================

    async def query_session_status(self, user_id: str, game_id: str) -> Optional[str]:
        session = await prisma.gamesession.find_first(
            where={"user_id": user_id, "game_id": game_id}
        )
        return session.id if session else None

    async def create_session(
        self,
        character_config: Dict[str, Any],
        game_id: str,
        user_id: str,
    ):
        if game_id not in GAME_REGISTRY:
            raise ValueError(f"Unknown game: {game_id}")
        if not await self.model_client.is_healthy():
            raise HTTPException(
                status_code=503,
                detail=f"Model server not available at {self.model_client.base_url}",
            )

        # Delete existing session for this user/game if it exists
        await self.delete_sessions(game_id=game_id, user_id=user_id)

        # Create initial states
        new_gamestate = GameState(game_id=game_id)
        new_playerstate = CharacterState(
            name=character_config["name"],
            strength=character_config["strength"],
            dexterity=character_config["dexterity"],
            constitution=character_config["constitution"],
            intelligence=character_config["intelligence"],
            wisdom=character_config["wisdom"],
            charisma=character_config["charisma"],
            character_type=CharacterType(character_config["character_type"]),
            bio=character_config["bio"],
        )

        gamesession_record = await prisma.gamesession.create(
            data={
                "user_id": user_id,
                "game_id": game_id,
                "is_active": True,
            }
        )

        await prisma.gamestate.create(
            data={
                "game_session_id": gamesession_record.id,
                **new_gamestate.to_db(for_create=True),
            }
        )

        await prisma.playerstate.create(
            data={
                "user_id": user_id,
                "game_session_id": gamesession_record.id,
                **new_playerstate.to_db(for_create=True),
            }
        )

        return {
            "session_id": gamesession_record.id,
        }

    # Get an existing sessions data
    async def get_session(self, game_id: str, session_id: str, user_id: str):
        """
        Load a session from DB
        """

        if not await self.model_client.is_healthy():
            raise HTTPException(
                status_code=503,
                detail=f"Model server not available at {self.model_client.base_url}",
            )

        gamesession_record, gamestate_record, playerstate_record = (
            await self.get_game_states_from_db(session_id=session_id, user_id=user_id)
        )

        # Get chat history
        chatmessage_records = await prisma.chatmessage.find_many(
            where={"session_id": gamesession_record.id}, order={"created_at": "asc"}
        )
        chat_history = [self.serialize_chat_message(msg) for msg in chatmessage_records]

        # Make sure engine is loaded with game states
        await self.ensure_engine_exists(game_id, gamesession_record.id, user_id)

    async def delete_sessions(self, game_id: str, user_id: str):
        sessions = await prisma.gamesession.find_many(
            where={"user_id": user_id, "game_id": game_id}
        )

        for session in sessions:
            await self.engine_manager.unregister_engine(
                game_id=game_id, session_id=session.id, is_save=False
            )

        # print("[DEBUG]Session to delete:", sessions)
        deleted = await prisma.gamesession.delete_many(
            where={"user_id": user_id, "game_id": game_id}
        )
        print("[DEBUG]Session deleted:", deleted)

    # ==========================================
    # GAME MANAGEMENT
    # ==========================================

    async def save_session(
        self, session_id: str, game_state: Dict[str, Any], player_state: Dict[str, Any]
    ):
        print("[DEBUG] SAVING SESSION")

        await prisma.gamesession.update(
            where={"id": session_id}, data={"is_active": False}
        )
        return

    async def save_player_state(self, player_state: Dict[str, Any]):
        print("[DEBUG] SAVING PLAYER STATE TO DB")
        await prisma.gamesession.update(
            where={"id": player_state.id}, data=player_state.model_dump()
        )
        return

    async def save_scene_state(self, scene_state: Dict[str, Any]):
        print("[DEBUG] SAVING SCENE STATE TO DB")
        await prisma.gamesession.update(
            where={"id": scene_state.id}, data=scene_state.model_dump()
        )
        return

    async def parse_action_request(
        self, session_id: str, action: str, game_id: str, user_id: str
    ):
        """
        Process player action and send results via WebSocket
        """

        try:
            # Ensure engine is loaded and get it directly
            engine_id, engine = await self.ensure_engine_exists(
                game_id, session_id, user_id
            )
            logger.info(f"Engine {engine_id} ready for session {session_id}")

            # Send immediate acknowledgment
            if hasattr(self, "connection_manager"):
                await self.connection_manager.send_to_session(
                    session_id, WebSocketMessage.action_received(action=action)
                )

            playerstate_record = await prisma.playerstate.find_first(
                where={"user_id": user_id, "game_session_id": session_id}
            )

            # Save the action as a chatmessage
            action_record = await prisma.chatmessage.create(
                {
                    "session_id": session_id,
                    "speaker": "player",
                    "action": "user_prompt",
                    "content": action,
                    "player_id": playerstate_record.id,
                },
            )

            # Send the action as a chat message first
            if hasattr(self, "connection_manager"):
                await self.connection_manager.send_to_session(
                    session_id,
                    WebSocketMessage.chat_message(
                        id=action_record.id,
                        speaker=action_record.speaker,
                        content=action_record.content,
                        timestamp=action_record.updated_at.isoformat(),
                    ),
                )

            narrated_action, player_state, game_condition = (
                await engine.execute_player_turn(action)
            )

            # Check if narrated_action is an error or exception
            if isinstance(narrated_action, dict) and narrated_action.get("type") in {
                "error",
                "exception",
            }:
                # Send the error message to the client
                if hasattr(self, "connection_manager"):
                    await self.connection_manager.send_to_session(
                        session_id,
                        WebSocketMessage.error(
                            narrated_action.get("message", "An unknown error occurred")
                        ),
                    )
                # Optionally log
                logger.warning(
                    f"Player action returned {narrated_action['type']}: {narrated_action.get('message')}"
                )
                return {"success": False, "game_condition": game_condition}

            # Normal case: valid action narrated_action
            player_turn_result = await prisma.chatmessage.create(
                {
                    "session_id": session_id,
                    "speaker": "narrator",
                    "action": narrated_action.action_type.value,  # assuming narrated_action has these attributes
                    "content": narrated_action.narration,
                    "player_id": playerstate_record.id,
                }
            )

            # Send narration to client
            if hasattr(self, "connection_manager"):
                await self.connection_manager.send_to_session(
                    session_id,
                    WebSocketMessage.player_action_result(
                        id=player_turn_result.id,
                        speaker=player_turn_result.speaker,
                        content=player_turn_result.content,
                        timestamp=player_turn_result.updated_at.isoformat(),
                        player_state=player_state,
                    ),
                )

            return {"success": True, "game_condition": game_condition}

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

    async def send_initial_state_to_session(
        self, game_state: Dict[str, Any], player_state: Dict[str, Any]
    ):
        session = await prisma.gamesession.find_first(
            where={"game_state": {"id": game_state["id"]}}
        )

        if not session:
            raise RuntimeError(f"No session found for GameState {game_state["id"]}")

        # Get chat history
        chatmessage_records = await prisma.chatmessage.find_many(
            where={"session_id": session.id}, order={"created_at": "asc"}
        )
        chat_history = [self.serialize_chat_message(msg) for msg in chatmessage_records]

        # Send initial state to WebSocket clients
        if hasattr(self, "connection_manager"):
            await self.connection_manager.send_to_session(
                session.id,
                WebSocketMessage.initial_state(
                    game_state=game_state,
                    player_state=player_state,
                    chat_history=chat_history,
                ),
            )
        return

    # NOTE: Should we save the state updates now?
    async def send_state_update_to_session(
        self, game_state: Dict[str, Any], player_state: Dict[str, Any]
    ):
        session = await prisma.gamesession.find_first(
            where={"game_state": {"id": game_state["id"]}}
        )

        if not session:
            raise RuntimeError(f"No session found for GameState {game_state["id"]}")

        if hasattr(self, "connection_manager"):
            await self.connection_manager.send_to_session(
                session.id,
                WebSocketMessage.session_state_update(game_state, player_state),
            )
        return

    # async def send_message_to_session(self, session_id: str, message: Dict[str, Any]):
    #     if hasattr(self, "connection_manager"):
    #         await self.connection_manager.send_to_session(
    #             session_id,
    #             WebSocketMessage.chat_message(
    #                 id=action_record.id,
    #                 speaker=action_record.speaker,
    #                 content=action_record.content,
    #                 timestamp=action_record.updated_at.isoformat(),
    #             ),
    #         )
    #     return

    # ==========================================
    # ENGINE METHODS
    # ==========================================

    async def start(self):
        await self.engine_manager.start()

    async def stop(self):
        await self.engine_manager.stop()

    def engine_factory(self, game_id: str):
        from backend.game.engine_registry import ENGINE_REGISTRY

        engine_name = GAME_REGISTRY[game_id]["engine"]
        if engine_name not in ENGINE_REGISTRY:
            raise ValueError(f"Engine not registered: {engine_name}")

        # Create Game Engine Instance
        engine_class = ENGINE_REGISTRY[engine_name]
        engine = engine_class(
            model_client=self.model_client,
            session_manager=self,
            event_bus=self.event_bus,
            game_id=game_id,
        )

        return engine

    async def ensure_engine_exists(
        self, game_id: str, session_id: str, user_id: str
    ) -> Tuple[str, Any]:
        """
        Ensure an engine exists for the session, creating one if needed.
        """

        # Check if engine is already registered and active
        result = self.engine_manager.get_registered_engine(game_id, session_id)
        if result:
            engine_id, engine = result
            logger.info(f"Using existing engine {engine_id} for session {session_id}")
            return engine_id, engine

        # No engine exists (expired or first time), create new one
        logger.info(f"Creating new engine for session {session_id}")

        # Get states and update session as active
        gamesession_record, gamestate_record, playerstate_record = (
            await self.get_game_states_from_db(session_id=session_id, user_id=user_id)
        )

        # Create and initialize engine
        engine_instance = self.engine_factory(game_id=game_id)

        engine_instance.load_game_state(
            game_state=gamestate_record,
            player_state=playerstate_record,
        )

        # Register the new engine
        engine_id = self.engine_manager.register_engine(
            engine_instance=engine_instance,
            session_id=session_id,
            game_id=game_id,
        )

        logger.info(f"Registered new engine {engine_id} for session {session_id}")
        return engine_id, engine_instance

    async def list_registered_engines(self):
        """
        List all currently registered engine instances
        """

        engine_instances = await self.engine_manager.list_registered_engines()

        if not engine_instances:
            raise ValueError("No instances found")
        return {"engine_instances": engine_instances}

    async def list_registered_engines_by_game(self, game_id: str):
        engine_instances = await self.engine_manager.list_registered_engines_by_game(
            game_id
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
            "timestamp": msg.updated_at.isoformat() if msg.updated_at else None,
        }

    async def get_game_states_from_db(self, session_id, user_id):
        gamesession_record = await prisma.gamesession.update(
            where={"id": session_id}, data={"is_active": True}
        )
        if not gamesession_record:
            raise HTTPException(
                status_code=404,
                detail=f"Couldn't locate session {session_id}",
            )

        gamestate_record = await prisma.gamestate.find_first(
            where={"game_session_id": gamesession_record.id}
        )
        if not gamestate_record:
            raise HTTPException(
                status_code=404,
                detail=f"Couldn't locate gamestate for session {gamesession_record.id}",
            )

        playerstate_record = await prisma.playerstate.find_first(
            where={"game_session_id": gamesession_record.id, "user_id": user_id}
        )
        if not playerstate_record:
            raise HTTPException(
                status_code=404,
                detail=f"Couldn't locate playerstate for session {gamesession_record.id} | user {user_id}",
            )

        return gamesession_record, gamestate_record, playerstate_record

    async def generate_initial_narration_for_session(
        self, session_id: str, game_id: str
    ):
        """
        Generate initial narration and send via WebSocket
        """

        try:
            # Get session data
            # gamesession_record = await prisma.gamesession.find_unique(
            #     where={"id": session_id}
            # )

            playerstate_record = await prisma.playerstate.find_first(
                where={"game_session_id": session_id}
            )
            print(playerstate_record.model_dump())
            if not playerstate_record:
                return

            # Load scene configuration
            with open(
                f"backend/game/dnd_engine/scenes/{game_id}/village.json", "r"
            ) as file:
                scene_conf = json.load(file)

            # # Create system message first
            # system_message = await prisma.chatmessage.create(
            #     data={
            #         "session_id": session_id,
            #         "speaker": "system",
            #         "action": "narrate",
            #         "content": scene_conf["session_start"]["description"],
            #     }
            # )

            # # Send system message via WebSocket immediately
            # if hasattr(self, "connection_manager"):
            #     await self.connection_manager.send_to_session(
            #         session_id,
            #         WebSocketMessage.chat_message(
            #             id=system_message.id,
            #             speaker=system_message.speaker,
            #             content=system_message.content,
            #             timestamp=system_message.updated_at.isoformat(),
            #         ),
            #     )

            # Generate AI narration
            scene_request = GenerateSceneRequest(
                scene=scene_conf["village_arrival"],
                player=playerstate_record.model_dump(),
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
                        timestamp=narrator_message.updated_at.isoformat(),
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
