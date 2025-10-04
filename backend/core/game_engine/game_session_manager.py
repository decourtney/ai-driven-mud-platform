import uuid
import json
import asyncio
import logging
from prisma import Json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, Union
from fastapi import HTTPException
from backend.services.api.server import prisma
from backend.services.api.models.scene_models import GenerateSceneRequest
from backend.core.characters.character_models import CharacterType
from backend.services.api.connection_manager import (
    ConnectionManager,
    WebSocketMessage,
)
from backend.game_registry import GAME_REGISTRY
from backend.core.game_engine.game_state import GameState
from backend.core.characters.player_character import PlayerCharacter
from backend.core.characters.npc_character import NpcCharacter

# from backend.game.engine_registry import ENGINE_REGISTRY
from backend.services.ai_models.model_client import AsyncModelServiceClient
from backend.core.game_engine.game_engine_manager import GameEngineManager
from backend.core.game_engine.event_bus import EventBus

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

        new_playerCharacter = PlayerCharacter(
            name=character_config["name"],
            strength=character_config["strength"],
            dexterity=character_config["dexterity"],
            constitution=character_config["constitution"],
            intelligence=character_config["intelligence"],
            wisdom=character_config["wisdom"],
            charisma=character_config["charisma"],
            character_type=character_config["character_type"],
            creature_type="HUMANOID",
            bio=character_config["bio"],
        )

        print("\033[93m[DEBUG] New PlayerCharacter:\033[0m", PlayerCharacter)

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

        base_character = await prisma.basecharacter.create(
            data={
                "name": new_playerCharacter.name,
                "bio": new_playerCharacter.bio,
                "character_type": new_playerCharacter.character_type,
                "creature_type": new_playerCharacter.creature_type,
                "game_session_id": gamesession_record.id,
            }
        )
        await prisma.playercharacter.create(
            data={
                "base_id": base_character.id,
                "level": new_playerCharacter.level,
                "max_hp": new_playerCharacter.max_hp,
                "current_hp": new_playerCharacter.current_hp,
                "temporary_hp": new_playerCharacter.temporary_hp,
                "armor_class": new_playerCharacter.armor_class,
                "initiative": new_playerCharacter.initiative,
                "initiative_bonus": new_playerCharacter.initiative_bonus,
                "strength": new_playerCharacter.strength,
                "dexterity": new_playerCharacter.dexterity,
                "constitution": new_playerCharacter.constitution,
                "intelligence": new_playerCharacter.intelligence,
                "wisdom": new_playerCharacter.wisdom,
                "charisma": new_playerCharacter.charisma,
                "gold": new_playerCharacter.gold,
                "experience": new_playerCharacter.experience,
                "natural_heal": new_playerCharacter.natural_heal,
                "current_zone": new_playerCharacter.current_zone,
                "current_scene": new_playerCharacter.current_scene,
                # PlayerCharacters tied to session and User
                "user_id": user_id,
                "game_session_id": gamesession_record.id,
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

        # get and update db entry
        gamesession_record = await prisma.gamesession.update(
            where={"id": session_id}, data={"is_active": True}
        )
        if not gamesession_record:
            raise HTTPException(
                status_code=404,
                detail=f"Couldn't locate session {session_id}",
            )

        # Make sure engine is loaded with game states
        await self.ensure_engine_exists(game_id, gamesession_record.id, user_id)

        return

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

    async def save_session(
        self, session_id: str, game_state: GameState, player_character: PlayerCharacter
    ):
        print("[DEBUG] SAVING SESSION")

        await prisma.gamesession.update(
            where={"id": session_id}, data={"is_active": False}
        )

        await prisma.gamestate.update(where={"id": game_state["id"]}, data=game_state)

        await self.save_player(player_character)

        return

    # async def get_session_id_using_game_state_id(
    #     self, game_state_id: str
    # ) -> Optional[str]:
    #     session = await prisma.gamesession.find_first(
    #         where={"game_state": {"id": game_state_id}}
    #     )
    #     if not session:
    #         raise RuntimeError(f"No session found for GameState {game_state_id}")

    #     return session.id if session else None

    # ==========================================
    # GAME MANAGEMENT
    # ==========================================

    async def save_player(self, player_character: PlayerCharacter):
        print("[DEBUG] SAVE PLAYER PROCESS STARTED")
        await self.save_base_character(player_character)
        await self.save_player_fields(player_character)
        await self.save_condition_effects(player_character)
        await self.save_inventory(player_character)
        await self.save_abilities(player_character)
        await self.save_spells(player_character)
        await self.save_spell_slots(player_character)
        await self.save_active_quests(player_character)

        return

    async def save_npc(self, npc_character: NpcCharacter):
        print("[DEBUG] SAVE NPC PROCESS STARTED")
        await self.save_base_character(npc_character)
        await self.save_npc_fields(npc_character)
        await self.save_condition_effects(npc_character)
        await self.save_inventory(npc_character)
        await self.save_abilities(npc_character)
        await self.save_spells(npc_character)
        return

    async def save_base_character(
        self, character: Union[PlayerCharacter, NpcCharacter]
    ):
        print("[DEBUG] SAVING BASE CHARACTER")
        print(character)
        base_data = character.model_dump(
            include={
                "name",
                "bio",
                "character_type",
                "creature_type",
            },
            exclude_none=True,
            mode="json",
        )

        await prisma.basecharacter.update(
            where={"id": character.base_id},
            data=base_data,
        )

        return

    async def save_player_fields(self, player_character: PlayerCharacter):
        print("[DEBUG] SAVING PLAYER CHARACTER")

        player_data = player_character.model_dump(
            include={
                "level",
                "max_hp",
                "current_hp",
                "temporary_hp",
                "armor_class",
                "initiative",
                "initiative_bonus",
                "strength",
                "dexterity",
                "constitution",
                "intelligence",
                "wisdom",
                "charisma",
                "gold",
                "experience",
                "natural_heal",
                "current_zone",
                "current_scene",
            },
            exclude_none=True,
            mode="json",
        )

        await prisma.playercharacter.update(
            where={"id": player_character.player_id},
            data=player_data,
        )

        return

    async def save_npc_fields(self, npc_character: NpcCharacter):
        print("[DEBUG] SAVING NPC CHARACTER")

        npc_data = npc_character.model_dump(
            include={
                "damage",
                "disposition",
                "loot_table",
                "available_quests",
            },
            exclude_none=True,
            mode="json",
        )

        await prisma.npccharacter.update(
            where={"id": npc_character.npc_id}, data=npc_data
        )

        return

    async def save_condition_effects(
        self, character: Union[PlayerCharacter, NpcCharacter]
    ):
        print("[DEBUG] SAVING CHARACTER CONDITIONS")

        # Delete all existing condition effects for this character
        await prisma.conditioneffectinstance.delete_many(
            where={"character_id": character.base_id}
        )

        # Insert current effects
        for condition in character.condition_effects:
            new_cond = await prisma.conditioneffectinstance.create(
                data={
                    "character_id": character.base_id,
                    "duration": condition.duration,
                    "intensity": condition.intensity,
                    "source": condition.source,
                    "effect": condition.effect,
                }
            )
            # Optionally attach new ID back to in-memory object
            condition.id = new_cond.id

        return

    async def save_inventory(self, character: Union[PlayerCharacter, NpcCharacter]):
        print("[DEBUG] SAVING CHARACTER INVENTORY")

        # Get a list of all current inventory items
        current_item_ids = {inv.item_id for inv in character.inventory}

        # Delete items not in current inventory
        await prisma.inventory.delete_many(
            where={
                "character_id": character.base_id,
                "item_id": {"not_in": list(current_item_ids)},
            }
        )

        for inv_item in character.inventory:
            await prisma.inventory.upsert(
                where={"id": inv_item.id} if inv_item.id else {"id": "DUMMY"},
                create={
                    "character_id": character.base_id,
                    "item_id": inv_item.item_id,
                    "quantity": inv_item.quantity,
                    "equipped": inv_item.equipped,
                },
                update={
                    "quantity": inv_item.quantity,
                    "equipped": inv_item.equipped,
                },
            )

        return

    async def save_abilities(self, character: Union[PlayerCharacter, NpcCharacter]):
        print("[DEBUG] SAVING CHARACTER ABILITIES")

        # Get the IDs currently in the player's abilities
        current_ability_ids = {ab.ability_id for ab in character.known_abilities}

        # Fetch existing ability links from DB
        existing_abilities = await prisma.abilityoncharacter.find_many(
            where={"character_id": character.base_id}
        )
        existing_ability_ids = {ab.ability_id for ab in existing_abilities}

        # Insert new abilities
        for ab in character.known_abilities:
            if ab.ability_id not in existing_ability_ids:
                await prisma.abilityoncharacter.create(
                    data={
                        "character_id": character.base_id,
                        "ability_id": ab.ability_id,
                        "level": getattr(ab, "level", 1),  # if you track levels
                    }
                )

        # Delete removed abilities
        for ab in existing_abilities:
            if ab.ability_id not in current_ability_ids:
                await prisma.abilityoncharacter.delete(where={"id": ab.id})

        return

    async def save_spells(self, character: PlayerCharacter):
        print("[DEBUG] SAVING CHARACTER SPELLS")

        # Get the IDs currently in the player's spells
        current_spell_ids = {sp.spell_id for sp in character.known_spells}

        # Fetch existing spell links from DB
        existing_spells = await prisma.spelloncharacter.find_many(
            where={"character_id": character.base_id}
        )
        existing_spell_ids = {sp.spell_id for sp in existing_spells}

        # Insert new spells
        for sp in character.known_spells:
            if sp.spell_id not in existing_spell_ids:
                await prisma.spelloncharacter.create(
                    data={
                        "character_id": character.base_id,
                        "spell_id": sp.spell_id,
                        "level": getattr(sp, "level", 1),  # optional
                        "prepared": getattr(sp, "prepared", False),
                    }
                )

        # Delete removed spells
        for sp in existing_spells:
            if sp.spell_id not in current_spell_ids:
                await prisma.spelloncharacter.delete(where={"id": sp.id})

    async def save_spell_slots(self, player_character: PlayerCharacter):
        print("[DEBUG] SAVING PLAYER SPELL SLOTS")

        # Get the IDs currently in the player's spell slots
        current_slots = {
            (slot.level, slot.id) for slot in player_character.spell_slots if slot.id
        }

        # Fetch existing spell slot links from DB
        existing_slots = await prisma.spellslot.find_many(
            where={"player_id": player_character.player_id}
        )
        existing_slots_map = {(slot.level, slot.id): slot for slot in existing_slots}

        # Insert new slots
        for slot in player_character.spell_slots:
            key = (slot.level, slot.id)
            if key not in existing_slots_map:
                await prisma.spellslot.create(
                    data={
                        "player_id": player_character.player_id,
                        "level": slot.level,
                        "used": slot.used,
                    }
                )

        # Delete removed slots
        for slot in existing_slots:
            key = (slot.level, slot.id)
            if key not in {(s.level, s.id) for s in player_character.spell_slots}:
                await prisma.spellslot.delete(where={"id": slot.id})

        # Update existing slots
        for slot in player_character.spell_slots:
            if slot.id in [s.id for s in existing_slots]:
                await prisma.spellslot.update(
                    where={"id": slot.id},
                    data={"used": slot.used},
                )

        return

    async def save_active_quests(self, player_character: PlayerCharacter):
        print("[DEBUG] SAVING PLAYER QUESTS")

        # --- Active Quests ---
        current_quest_ids = {
            q.quest_id for q in player_character.active_quests.values()
        }

        existing_quests = await prisma.queststate.find_many(
            where={"player_id": player_character.id}
        )
        existing_quest_ids = {q.quest_id for q in existing_quests}

        # Insert new quests
        for q in player_character.active_quests.values():
            if q.quest_id not in existing_quest_ids:
                await prisma.queststate.create(
                    data={
                        "player_id": player_character.id,
                        "quest_id": q.quest_id,
                        "status": q.status,
                        "objectives": (
                            q.objectives.dict()
                            if hasattr(q.objectives, "dict")
                            else q.objectives
                        ),
                        "created_at": q.started_at,
                        "completed_at": q.completed_at,
                    }
                )

        # Delete removed quests
        for q in existing_quests:
            if q.quest_id not in current_quest_ids:
                await prisma.queststate.delete(where={"id": q.id})

        # Update existing quests
        for q in player_character.active_quests.values():
            if q.quest_id in existing_quest_ids:
                db_q = next(
                    (x for x in existing_quests if x.quest_id == q.quest_id), None
                )
                if db_q:
                    await prisma.queststate.update(
                        where={"id": db_q.id},
                        data={
                            "status": q.status,
                            "objectives": (
                                q.objectives.dict()
                                if hasattr(q.objectives, "dict")
                                else q.objectives
                            ),
                            "completed_at": q.completed_at,
                        },
                    )

        return

    async def save_scene_diff(self, scene_state: Dict[str, Any]):
        print("[DEBUG] SAVING SCENE DIFF TO DB")

        await prisma.gamesession.update(
            where={"id": scene_state.id}, data=scene_state.model_dump()
        )
        return

    async def lock_player_input(
        self,
        is_locked: bool,
        session_id: Optional[str] = None,
        game_state_id: Optional[str] = None,
    ):
        if game_state_id:
            session = await prisma.gamesession.find_first(
                where={"game_state": {"id": game_state_id}}
            )
        session_id = session_id or session.id

        if not session_id:
            raise RuntimeError(f"No session found for GameState {game_state_id}")

        if hasattr(self, "connection_manager"):
            await self.connection_manager.send_to_session(
                session_id, WebSocketMessage.lock_player_input(is_locked=is_locked)
            )
        return

    async def process_player_action(
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

            # Lock player input to prevent concurrent actions - comment out for testing input
            asyncio.create_task(
                self.lock_player_input(is_locked=True, session_id=session_id)
            )

            # Send immediate acknowledgment
            if hasattr(self, "connection_manager"):
                await self.connection_manager.send_to_session(
                    session_id, WebSocketMessage.action_received(action=action)
                )

            playercharacter_record = await prisma.playercharacter.find_first(
                where={"user_id": user_id, "game_session_id": session_id}
            )

            message = {
                "speaker": "PLAYER",
                "action": "USER_PROMPT",
                "content": action,
                "player_id": playercharacter_record.id,
            }

            # Send the action as a chat message first
            asyncio.create_task(
                self.send_message_to_session(session_id=session_id, message=message)
            )

            asyncio.create_task(engine.execute_player_action(action))

            return

        except Exception as e:
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
        self, game_state: Dict[str, Any], player_character: Dict[str, Any]
    ):
        session = await prisma.gamesession.find_first(
            where={"game_state": {"id": game_state["id"]}}
        )
        print("initial state:", session)
        if not session:
            raise RuntimeError(f"No session found for GameState {game_state["id"]}")

        # Get chat history
        chatmessage_records = await prisma.chatmessage.find_many(
            where={"game_session_id": session.id}, order={"created_at": "asc"}
        )
        chat_history = [self.serialize_chat_record(msg) for msg in chatmessage_records]

        # Send initial state to WebSocket clients
        if hasattr(self, "connection_manager"):
            await self.connection_manager.send_to_session(
                session.id,
                WebSocketMessage.initial_state(
                    game_state=game_state,
                    player_character=player_character,
                    chat_history=chat_history,
                ),
            )

    # NOTE: Should we save the state updates now?
    async def send_state_update_to_session(
        self, game_state: GameState, player_character: PlayerCharacter
    ):
        session = await prisma.gamesession.find_first(
            where={"game_state": {"id": game_state["id"]}}
        )

        gamestate_record = await prisma.gamestate.update(
            where={"id": game_state["id"]}, data=game_state
        )

        await self.save_player(player_character)

        if not session:
            raise RuntimeError(f"No session found for GameState {game_state["id"]}")

        if hasattr(self, "connection_manager"):
            await self.connection_manager.send_to_session(
                session.id,
                WebSocketMessage.session_state_update(game_state, player_character),
            )
        return

    async def send_message_to_session(
        self, message: Dict[str, Any], session_id: str, message_id: Optional[str] = None
    ):
        if not session_id:
            raise RuntimeError(f"No session iD")

        chatmessage_record = await prisma.chatmessage.create(
            {
                "game_session_id": session_id,
                "speaker": message["speaker"],
                "action": message["action"],
                "content": message["content"],
            }
        )

        if not chatmessage_record:
            raise RuntimeError(f"Failed to save chat message for session: {session_id}")

        if hasattr(self, "connection_manager"):
            await self.connection_manager.send_to_session(
                session_id,
                WebSocketMessage.chat_message(
                    id=message_id or chatmessage_record.id,
                    speaker=chatmessage_record.speaker,
                    content=chatmessage_record.content,
                    timestamp=chatmessage_record.updated_at.isoformat(),
                    typing=message.get("typing", False),
                ),
            )
        return

    async def send_player_action_to_session(
        self,
        message: Dict[str, Any],
        player_character: Dict[str, Any],
        session_id: Optional[str] = None,
        game_state_id: Optional[str] = None,
    ):
        session = None

        if game_state_id:
            session = await prisma.gamesession.find_first(
                where={"game_state": {"id": game_state_id}}
            )
            if session:
                session_id = session.id

        if not session_id:
            raise RuntimeError(f"No session found for GameState {game_state_id}")

        chatmessage_record = await prisma.chatmessage.create(
            {
                "game_session_id": session_id,
                "player_id": player_character["id"],
                **message,
            }
        )

        if hasattr(self, "connection_manager"):
            await self.connection_manager.send_to_session(
                session_id,
                WebSocketMessage.player_action_result(
                    id=chatmessage_record.id,
                    speaker=chatmessage_record.speaker,
                    content=chatmessage_record.content,
                    timestamp=chatmessage_record.updated_at.isoformat(),
                    player_character=player_character,
                ),
            )

    async def send_streaming_message(
        self,
        message: Dict[str, Any],
        session_id: str,
        timestamp: Optional[str] = "",
        message_id: Optional[str] = None,
    ):
        """Send streaming update to WebSocket without saving to database"""
        if not session_id:
            raise RuntimeError(f"No session Id found")

        if not message_id:
            message_id = str(uuid.uuid4())

        if hasattr(self, "connection_manager"):
            await self.connection_manager.send_to_session(
                session_id,
                WebSocketMessage.streaming_message(
                    id=message_id,
                    speaker=message.get("speaker"),
                    content=message.get("content"),
                    timestamp=timestamp,
                    typing=message.get("typing", False),
                ),
            )

        return message_id

    async def save_streamed_message(
        self, message: Dict[str, Any], session_id: str, message_id: Optional[str] = None
    ):
        if not session_id:
            raise RuntimeError(f"No session iD")

        chatmessage_record = await prisma.chatmessage.create(
            {
                "id": message_id,
                "game_session_id": session_id,
                "speaker": message["speaker"],
                "action": message["action"],
                "content": message["content"],
            }
        )
        return chatmessage_record

    # ==========================================
    # ENGINE METHODS
    # ==========================================

    async def start(self):
        await self.engine_manager.start()

    async def stop(self):
        await self.engine_manager.stop()

    def engine_factory(self, game_id: str, session_id: str):
        from backend.engine_registry import ENGINE_REGISTRY

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
            session_id=session_id,
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

        # Create and initialize engine
        engine_instance = self.engine_factory(game_id=game_id, session_id=session_id)

        # Register the new engine
        engine_id = self.engine_manager.register_engine(
            engine_instance=engine_instance,
            session_id=session_id,
            game_id=game_id,
        )

        # Get states and update session as active
        gamesession_record, gamestate_record, playercharacter_record = (
            await self.get_game_records_from_db(session_id=session_id, user_id=user_id)
        )

        await engine_instance.load_game_state(
            game_state=gamestate_record,
            player_character=playercharacter_record.model_dump(),
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

    def serialize_chat_record(self, msg):
        return {
            "id": msg.id,
            "speaker": msg.speaker,
            "action": msg.action,
            "content": msg.content,
            "timestamp": msg.updated_at.isoformat() if msg.updated_at else None,
        }

    async def get_game_records_from_db(self, session_id, user_id):
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

        playercharacter_record = await prisma.playercharacter.find_first(
            where={"game_session_id": gamesession_record.id, "user_id": user_id},
            include={
                "base": {
                    "include": {
                        "condition_effects": True,
                        "inventory": True,
                        "abilities": True,
                        "spells": True,
                    }
                },
                "spell_slots": True,
                "active_quests": True,
            },
        )
        if not playercharacter_record:
            raise HTTPException(
                status_code=404,
                detail=f"Couldn't locate player_character for session {gamesession_record.id} | user {user_id}",
            )

        return gamesession_record, gamestate_record, playercharacter_record
