"""
FastAPI server optimized for Next.js frontend integration.
Provides clean REST endpoints and WebSocket streaming for real-time gameplay.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import uvicorn
import json
import asyncio
import uuid
from datetime import datetime
from pydantic import BaseModel

from game.core.game_engine import GameEngine, GameCondition
from game.core.model_manager import ModelManager
from game.core.character_state import CharacterState


# API Models for Next.js integration
class GameSessionCreate(BaseModel):
    player_name: str
    character_class: Optional[str] = "Fighter"
    scenario: Optional[str] = "dungeon_exploration"

class GameSessionResponse(BaseModel):
    session_id: str
    status: str
    scene_description: str
    player_status: dict
    npcs_status: list
    turn_number: int
    
class PlayerActionRequest(BaseModel):
    session_id: str
    action: str
    
class PlayerActionResponse(BaseModel):
    success: bool
    narration: str
    game_condition: str
    should_continue: bool
    
class NPCActionResponse(BaseModel):
    npc_name: str
    narration: str
    success: bool

class TurnCompleteResponse(BaseModel):
    scene_description: str
    game_condition: str
    turn_number: int
    

class GameSession:
    """Represents an active game session"""
    def __init__(self, session_id: str, player_name: str):
        self.session_id = session_id
        self.player_name = player_name
        self.engine: Optional[GameEngine] = None
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.game_condition = GameCondition.CONTINUE
        self.websocket: Optional[WebSocket] = None
        
    def to_dict(self) -> dict:
        """Convert session to dict for API responses"""
        if not self.engine or not self.engine.game_state:
            return {
                "session_id": self.session_id,
                "status": "initializing",
                "scene_description": "Loading...",
                "player_status": {},
                "npcs_status": [],
                "turn_number": 0
            }
            
        return {
            "session_id": self.session_id,
            "status": "active" if self.game_condition == GameCondition.CONTINUE else self.game_condition.value,
            "scene_description": self.engine.get_current_scene(),
            "player_status": {
                "name": self.engine.game_state.player.name,
                "hp": self.engine.game_state.player.current_hp,
                "max_hp": self.engine.game_state.player.max_hp,
                "alive": self.engine.game_state.player.is_alive()
            },
            "npcs_status": [
                {
                    "name": npc.name,
                    "hp": npc.current_hp,
                    "max_hp": npc.max_hp,
                    "alive": npc.is_alive()
                }
                for npc in self.engine.game_state.npcs
            ],
            "turn_number": self.engine.game_state.turn_counter
        }


class DNDGameServer:
    """
    Next.js optimized game server with clean REST API and WebSocket streaming.
    """
    
    def __init__(self, model_manager: Optional[ModelManager] = None):
        self.model_manager = model_manager or ModelManager()
        self.active_sessions: Dict[str, GameSession] = {}
        self.app = self._create_app()
    
    def load_all_models(self) -> dict[str, bool]:
        """Load all models and return status"""
        try:
            success = self.model_manager.load_all_models()
            return {
                "models_manager": success,
                "parser_ready": self.model_manager.is_parser_ready(),
                "narrator_ready": self.model_manager.is_narrator_ready()
            }
        except Exception as e:
            print(f"[-] Error loading models: {e}")
            return {"models_manager": False, "parser_ready": False, "narrator_ready": False}
    
    def _create_sample_game_state(self, player_name: str) -> tuple[CharacterState, List[CharacterState], dict]:
        """Create sample game state for testing (replace with actual character creation)"""
        player = CharacterState(
            name=player_name,
            max_hp=20,
            current_hp=20,
            equipped_weapon="sword"
        )
        
        npcs = [
            CharacterState(name="Goblin", max_hp=8, current_hp=8, equipped_weapon="club"),
            CharacterState(name="Orc", max_hp=15, current_hp=15, equipped_weapon="axe")
        ]
        
        scene = {
            "name": "Dark Dungeon",
            "description": "A dank stone corridor lit by flickering torches",
            "rules": {},
            "difficulty_modifier": 0
        }
        
        return player, npcs, scene
    
    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application"""
        app = FastAPI(
            title="D&D Streaming Game API", 
            version="4.0.0",
            description="Real-time D&D game engine optimized for Next.js frontend"
        )
        
        # CORS for Next.js development
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev servers
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Health check endpoint
        @app.get("/health")
        def health_check():
            return {
                "status": "healthy",
                "models_loaded": self.model_manager.are_models_loaded(),
                "active_sessions": len(self.active_sessions),
                "components": {
                    "parser": self.model_manager.is_parser_ready(),
                    "narrator": self.model_manager.is_narrator_ready()
                }
            }
        
        # Game session management
        @app.post("/sessions", response_model=GameSessionResponse)
        def create_game_session(request: GameSessionCreate):
            """Create a new game session"""
            try:
                if not self.model_manager.are_models_loaded():
                    raise HTTPException(status_code=503, detail="Models not loaded")
                
                session_id = str(uuid.uuid4())
                session = GameSession(session_id, request.player_name)
                
                # Initialize game engine
                session.engine = GameEngine(self.model_manager)
                player, npcs, scene_state = self._create_sample_game_state(request.player_name)
                session.engine.initialize_game_state(player, npcs, scene_state)
                
                self.active_sessions[session_id] = session
                
                return GameSessionResponse(**session.to_dict())
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")
        
        @app.get("/sessions/{session_id}", response_model=GameSessionResponse)
        def get_game_session(session_id: str):
            """Get current game session state"""
            if session_id not in self.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.active_sessions[session_id]
            session.last_activity = datetime.now()
            return GameSessionResponse(**session.to_dict())
        
        @app.delete("/sessions/{session_id}")
        def delete_game_session(session_id: str):
            """End a game session"""
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                return {"success": True, "message": "Session ended"}
            raise HTTPException(status_code=404, detail="Session not found")
        
        @app.get("/sessions")
        def list_sessions():
            """List all active sessions (for debugging)"""
            return {
                "active_sessions": len(self.active_sessions),
                "sessions": [
                    {
                        "session_id": session.session_id,
                        "player_name": session.player_name,
                        "created_at": session.created_at.isoformat(),
                        "status": session.game_condition.value
                    }
                    for session in self.active_sessions.values()
                ]
            }
        
        # Game actions - streaming endpoints
        @app.post("/sessions/{session_id}/action", response_model=PlayerActionResponse)
        def process_player_action(session_id: str, request: PlayerActionRequest):
            """Process player action and return immediate result"""
            if session_id not in self.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.active_sessions[session_id]
            if not session.engine:
                raise HTTPException(status_code=500, detail="Game engine not initialized")
            
            try:
                # Process player action immediately
                narration, condition, should_continue = session.engine.process_player_input_immediate(request.action)
                session.game_condition = condition
                session.last_activity = datetime.now()
                
                return PlayerActionResponse(
                    success=True,
                    narration=narration,
                    game_condition=condition.value,
                    should_continue=should_continue
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Action processing failed: {str(e)}")
        
        @app.get("/sessions/{session_id}/npcs/actions")
        def get_npc_actions(session_id: str):
            """Get and process all NPC actions for this turn"""
            if session_id not in self.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.active_sessions[session_id]
            if not session.engine:
                raise HTTPException(status_code=500, detail="Game engine not initialized")
            
            try:
                living_npcs = session.engine.get_living_npcs()
                npc_results = []
                
                for npc in living_npcs:
                    narration, success = session.engine.process_single_npc_action(npc)
                    if narration:
                        npc_results.append(NPCActionResponse(
                            npc_name=npc.name,
                            narration=narration,
                            success=success
                        ))
                
                # Update game condition after NPC actions
                session.game_condition = session.engine.check_game_condition()
                session.last_activity = datetime.now()
                
                return {
                    "npc_actions": npc_results,
                    "game_condition": session.game_condition.value
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"NPC processing failed: {str(e)}")
        
        @app.get("/sessions/{session_id}/scene", response_model=TurnCompleteResponse)
        def get_updated_scene(session_id: str):
            """Get updated scene description after all actions"""
            if session_id not in self.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.active_sessions[session_id]
            if not session.engine:
                raise HTTPException(status_code=500, detail="Game engine not initialized")
            
            try:
                scene_description, final_condition = session.engine.get_updated_scene_after_actions()
                session.game_condition = final_condition
                session.last_activity = datetime.now()
                
                turn_number = session.engine.game_state.turn_counter if session.engine.game_state else 0
                
                return TurnCompleteResponse(
                    scene_description=scene_description,
                    game_condition=final_condition.value,
                    turn_number=turn_number
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Scene update failed: {str(e)}")
        
        # WebSocket for real-time streaming
        @app.websocket("/sessions/{session_id}/stream")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            """WebSocket endpoint for real-time game streaming"""
            await websocket.accept()
            
            if session_id not in self.active_sessions:
                await websocket.send_json({"error": "Session not found"})
                await websocket.close()
                return
            
            session = self.active_sessions[session_id]
            session.websocket = websocket
            
            try:
                while True:
                    # Wait for player action from frontend
                    data = await websocket.receive_json()
                    
                    if data.get("type") == "player_action":
                        # Stream the complete turn
                        await self._stream_complete_turn(websocket, session, data.get("action", ""))
                    elif data.get("type") == "get_scene":
                        # Send current scene
                        scene = session.engine.get_current_scene() if session.engine else "Loading..."
                        await websocket.send_json({
                            "type": "scene_update",
                            "scene": scene
                        })
                        
            except WebSocketDisconnect:
                session.websocket = None
                print(f"WebSocket disconnected for session {session_id}")
            except Exception as e:
                await websocket.send_json({"error": f"WebSocket error: {str(e)}"})
                session.websocket = None
        
        async def _stream_complete_turn(self, websocket: WebSocket, session: GameSession, action: str):
            """Stream a complete game turn with real-time updates"""
            try:
                # 1. Process player action
                await websocket.send_json({"type": "processing", "message": "Processing your action..."})
                
                narration, condition, should_continue = session.engine.process_player_input_immediate(action)
                await websocket.send_json({
                    "type": "player_result",
                    "narration": narration,
                    "condition": condition.value
                })
                
                if condition != GameCondition.CONTINUE or not should_continue:
                    await websocket.send_json({"type": "game_end", "condition": condition.value})
                    return
                
                # 2. Process NPCs
                await websocket.send_json({"type": "processing", "message": "NPCs are taking their turns..."})
                
                living_npcs = session.engine.get_living_npcs()
                for npc in living_npcs:
                    await websocket.send_json({"type": "npc_thinking", "npc": npc.name})
                    
                    narration, success = session.engine.process_single_npc_action(npc)
                    if narration:
                        await websocket.send_json({
                            "type": "npc_result",
                            "npc": npc.name,
                            "narration": narration
                        })
                
                # 3. Update scene
                await websocket.send_json({"type": "processing", "message": "Updating scene..."})
                
                scene_description, final_condition = session.engine.get_updated_scene_after_actions()
                session.game_condition = final_condition
                
                await websocket.send_json({
                    "type": "turn_complete",
                    "scene": scene_description,
                    "condition": final_condition.value,
                    "session_state": session.to_dict()
                })
                
            except Exception as e:
                await websocket.send_json({"error": f"Turn processing error: {str(e)}"})
        
        # Model management endpoints
        @app.post("/admin/load_models")
        def load_models():
            """Load all models"""
            try:
                results = self.load_all_models()
                return {"success": results["models_manager"], "results": results}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        @app.post("/admin/unload_models")
        def unload_models():
            """Unload all models"""
            try:
                self.model_manager.unload_all_models()
                return {"success": True, "message": "Models unloaded"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return app
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the server"""
        print(f"[+] Starting D&D Game Server v4.0 (Next.js optimized)...")
        print(f"[+] Server running on http://{host}:{port}")
        print(f"[+] API docs at http://{host}:{port}/docs")
        print(f"[+] WebSocket streaming available at ws://{host}:{port}/sessions/{{session_id}}/stream")
        
        uvicorn.run(self.app, host=host, port=port)


# Factory function for easy server creation  
def create_server(
    parser_model_path: Optional[str] = None,
    narrator_model_path: Optional[str] = None,
    narrator_adapter_path: Optional[str] = None
) -> DNDGameServer:
    """Factory function to create configured server"""
    model_manager = ModelManager(
        parser_model_path=parser_model_path,
        narrator_model_path=narrator_model_path,
        narrator_adapter_path=narrator_adapter_path
    )
    
    return DNDGameServer(model_manager=model_manager)


if __name__ == "__main__":
    server = create_server()
    
    # Load models at startup
    print("[+] Loading models at startup...")
    results = server.load_all_models()
    if results["models_manager"]:
        print("[+] Models loaded successfully!")
    else:
        print("[-] Warning: Failed to load models")
    
    server.run()