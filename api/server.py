"""
FastAPI server that orchestrates the D&D narrator system.
Clean separation of concerns - this only handles HTTP API logic.
"""

from fastapi import FastAPI, HTTPException
from typing import Optional
import uvicorn

from core.game_engine import GameEngine
from core.models import (
    HealthResponse, ParsedAction, ActionType, DamageType, 
    StructuredActionRequest, ProcessUserInputRequest
)
from parsers.codellama_parser import CodeLlamaParser
from narrators.pygmalion_narrator import PygmalionNarrator
from core.interfaces import ActionParser, ActionNarrator
from core.model_manager import ModelManager


class DNDServer:
    """
    Main server class that manages the application lifecycle.
    Uses ModelManager for efficient model loading/unloading.
    """
    
    def __init__(self, model_manager: Optional[ModelManager] = None):
        # Initialize model manager
        self.model_manager = model_manager or ModelManager()
        
        # Create game engine with model manager
        self.game_engine = GameEngine(self.model_manager)
        
        # Create FastAPI app
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
            return {
                "models_manager": False,
                "parser_ready": False, 
                "narrator_ready": False
            }
    
    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application"""
        app = FastAPI(
            title="D&D Narrator API", 
            version="3.0.0",
            description="Natural language D&D action processing with AI narration"
        )
        
        # Health check endpoint
        @app.get("/health", response_model=HealthResponse)
        def health_check():
            return HealthResponse(
                status="healthy",
                components={
                    "parser": self.model_manager.is_parser_ready(),
                    "narrator": self.model_manager.is_narrator_ready(),
                    "game_engine": True
                }
            )
        
        # Main natural language processing endpoint
        @app.post("/process_input")
        def process_input(request: ProcessUserInputRequest):
            """Process natural language input and return narrated result"""
            try:
                # Ensure models are loaded
                if not self.model_manager.are_models_loaded():
                    raise HTTPException(status_code=503, detail="Models not loaded")
                
                result = self.game_engine.execute_game_turn(request)
                
                # Convert to API response format
                return {
                    "actor": result.parsed_action.actor,
                    "action": result.parsed_action.action,
                    "target": result.parsed_action.target,
                    "action_type": result.parsed_action.action_type.value,
                    "weapon": result.parsed_action.weapon,
                    "subject": result.parsed_action.subject,
                    "details": result.parsed_action.details,
                    "dice_roll": result.dice_roll,
                    "hit": result.hit,
                    "damage_type": result.damage_type.value,
                    "narration": result.narration,
                    "difficulty": result.difficulty,
                    "parsing_method": result.parsed_action.parsing_method
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Action processing failed: {str(e)}")
        
        # Legacy endpoint for backwards compatibility
        @app.post("/process_structured_action")
        def test_process_structured_action(request: StructuredActionRequest):
            """For quick testing of structured action processing"""
            try:                
                result = self.game_engine.process_structured_action(
                    request.parsed_action, request.hit, request.damage_type
                )
                return result
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Legacy action processing failed: {str(e)}")
        
        @app.post("/process_user_input")
        def test_process_user_input(request: ProcessUserInputRequest):
            """For quick testing of user input processing"""
            try:
                if not self.model_manager.is_parser_ready():
                    raise HTTPException(status_code=503, detail="Parser not loaded")
                
                parsed_action = self.game_engine.process_user_input(request.user_input)
                
                return {
                    "actor": parsed_action.actor,
                    "action": parsed_action.action,
                    "target": parsed_action.target,
                    "action_type": parsed_action.action_type.value,
                    "weapon": parsed_action.weapon,
                    "subject": parsed_action.subject,
                    "details": parsed_action.details,
                    "parsing_method": parsed_action.parsing_method
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"User input processing failed: {str(e)}")
        
        # Model management endpoints
        @app.post("/load_models")
        def load_models():
            """Load both models"""
            try:
                results = self.load_all_models()
                success = results["models_manager"]
                return {
                    "success": success,
                    "results": results,
                    "message": "Models loaded successfully" if success else "Failed to load models"
                }
            except Exception as e:
                return {"success": False, "message": f"Error: {str(e)}"}
        
        @app.post("/unload_models")
        def unload_models():
            """Unload all models (free GPU memory)"""
            try:
                self.model_manager.unload_all_models()
                return {
                    "success": True,
                    "message": "All models unloaded"
                }
            except Exception as e:
                return {"success": False, "message": f"Error: {str(e)}"}
        
        @app.get("/model_status")
        def model_status():
            """Get current model loading status"""
            return {
                "parser_loaded": self.model_manager.is_parser_ready(),
                "narrator_loaded": self.model_manager.is_narrator_ready(),
                "both_loaded": self.model_manager.are_models_loaded(),
                "gpu_memory": self.model_manager.get_memory_usage()
            }
        
        # Legacy endpoints for compatibility
        @app.post("/reload_parser")
        def reload_parser():
            """Legacy endpoint - now loads both models"""
            return load_models()
        
        @app.post("/reload_narrator") 
        def reload_narrator():
            """Legacy endpoint - now loads both models"""
            return load_models()
        
        @app.post("/reload_all")
        def reload_all():
            """Legacy endpoint - now loads both models"""
            return load_models()
        
        return app
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the server"""
        print(f"[+] Starting D&D Narrator Server v3.0...")
        print(f"[+] Server running on http://{host}:{port}")
        print(f"[+] API docs at http://{host}:{port}/docs")
        
        # Show model status
        status = {
            "parser_ready": self.model_manager.is_parser_ready(),
            "narrator_ready": self.model_manager.is_narrator_ready()
        }
        print(f"[+] Model status: {status}")
        
        uvicorn.run(self.app, host=host, port=port)


# Factory function for easy server creation  
def create_server(
    parser_model_path: Optional[str] = None,
    narrator_model_path: Optional[str] = None,
    narrator_adapter_path: Optional[str] = None
) -> DNDServer:
    """Factory function to create configured server"""
    
    # Create model manager with optional custom paths
    model_manager = ModelManager(
        parser_model_path=parser_model_path,
        narrator_model_path=narrator_model_path,
        narrator_adapter_path=narrator_adapter_path
    )
    
    return DNDServer(model_manager=model_manager)


# Entry point when run directly
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