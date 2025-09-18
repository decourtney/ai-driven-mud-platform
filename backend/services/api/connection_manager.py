"""
WebSocket Connection Manager for D&D Game Engine
Handles real-time communication between clients and the game server.
"""

from websockets.exceptions import ConnectionClosedError
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Any
import json
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for game sessions"""

    def __init__(self):
        # Map of session_id -> list of WebSocket connections
        self.connections: Dict[str, List[WebSocket]] = {}
        # Map of WebSocket -> session info for cleanup
        self.websocket_sessions: Dict[WebSocket, Dict[str, str]] = {}

    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        """Connect a client to a game session"""
        await websocket.accept()

        # Initialize session connections if first time
        if session_id not in self.connections:
            self.connections[session_id] = []

        # Add connection to session
        self.connections[session_id].append(websocket)

        # Store session info for this websocket
        self.websocket_sessions[websocket] = {
            "session_id": session_id,
            "user_id": user_id,
            "connected_at": datetime.now().isoformat(),
        }

        logger.info(f"Client {user_id} connected to session {session_id}")

        # Send connection confirmation
        await self.send_to_client(
            websocket,
            {
                "type": "connection_confirmed",
                "session_id": session_id,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def disconnect(self, websocket: WebSocket):
        """Disconnect a client"""
        if websocket in self.websocket_sessions:
            session_info = self.websocket_sessions[websocket]
            session_id = session_info["session_id"]
            user_id = session_info["user_id"]

            # Remove from session connections
            if session_id in self.connections:
                self.connections[session_id] = [
                    conn for conn in self.connections[session_id] if conn != websocket
                ]

                # Clean up empty sessions
                if not self.connections[session_id]:
                    del self.connections[session_id]

            # Remove websocket session info
            del self.websocket_sessions[websocket]

            logger.info(f"Client {user_id} disconnected from session {session_id}")

    async def send_to_client(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to a specific client"""
        # Check if websocket is still in our managed connections
        if websocket not in self.websocket_sessions:
            logger.warning("WebSocket not in managed sessions, skipping send")
            return

        try:
            # Check WebSocket state before sending
            if websocket.client_state.name == "CONNECTED":
                await websocket.send_text(json.dumps(message))
            else:
                logger.warning(
                    f"WebSocket state is {websocket.client_state.name}, skipping send"
                )
                self.disconnect(websocket)
        except ConnectionClosedError:
            logger.info("Connection closed, cleaning up websocket")
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Failed to send message to client: {e}")
            self.disconnect(websocket)

    async def send_to_session(self, session_id: str, message: Dict[str, Any]):
        """Send message to all clients in a session"""
        if session_id not in self.connections:
            logger.warning(f"No connections found for session {session_id}")
            return

        # Send to all connections in the session
        disconnected = []
        for websocket in self.connections[session_id]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to session client: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get info about a session's connections"""
        if session_id not in self.connections:
            return {"connected_clients": 0, "clients": []}

        clients = []
        for websocket in self.connections[session_id]:
            if websocket in self.websocket_sessions:
                session_info = self.websocket_sessions[websocket]
                clients.append(
                    {
                        "user_id": session_info["user_id"],
                        "connected_at": session_info["connected_at"],
                    }
                )

        return {"connected_clients": len(clients), "clients": clients}


# Message types for WebSocket communication
class MessageType:
    # Client -> Server
    PLAYER_ACTION = "player_action"
    PING = "ping"

    # Server -> Client
    ACTION_RESULT = "action_result"
    GAME_STATE_UPDATE = "game_state_update"
    CHAT_MESSAGE = "chat_message"
    ERROR = "error"
    PONG = "pong"


class WebSocketMessage:
    """Helper class for creating standardized WebSocket messages"""

    @staticmethod
    def initial_state(
        game_state: Dict[str, Any],
        player_state: Dict[str, Any],
        chat_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create initial state message"""
        return {
            "type": "initial_state",
            "data": {
                "game_state": game_state,
                "player_state": player_state,
                "chat_history": chat_history,
            },
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def action_received(action: str) -> Dict[str, Any]:
        """Create action received acknowledgment"""
        return {
            "type": "action_received",
            "data": {"action": action},
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def chat_message(
        id: str, speaker: str, content: str, timestamp: str
    ) -> Dict[str, Any]:
        """Create chat message"""
        return {
            "type": MessageType.CHAT_MESSAGE,
            "data": {
                "id": id,
                "speaker": speaker,
                "content": content,
                "timestamp": timestamp,
            },
        }

    @staticmethod
    def player_action_result(
        narration: str, action: str, user_id: str
    ) -> Dict[str, Any]:
        """Create action result message"""
        return {
            "type": MessageType.ACTION_RESULT,
            "data": {
                "narration": narration,
                "original_action": action,
                "user_id": user_id,
            },
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def error(message: str, error_code: Optional[str] = None) -> Dict[str, Any]:
        """Create error message"""
        return {
            "type": MessageType.ERROR,
            "data": {"message": message, "error_code": error_code},
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def pong() -> Dict[str, Any]:
        """Create pong response"""
        return {"type": MessageType.PONG, "timestamp": datetime.now().isoformat()}

    @staticmethod
    def game_state_update(updates: Dict[str, Any]) -> Dict[str, Any]:
        """Create game state update message"""
        return {
            "type": MessageType.GAME_STATE_UPDATE,
            "data": updates,
            "timestamp": datetime.now().isoformat(),
        }
