#!/usr/bin/env python3
"""
Main entry point for the D&D Streaming Game Engine server.
Now uses decoupled model service for AI inference.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.services.api.server import create_server

# ==========================================
# Configuration
# ==========================================
MODEL_SERVER_URL = os.getenv("MODEL_SERVER_URL", "http://localhost:8001")
WAIT_FOR_MODELS = os.getenv("WAIT_FOR_MODELS", "true").lower() == "true"
AUTO_LOAD_MODELS = os.getenv("AUTO_LOAD_MODELS", "false").lower() == "true"

# ==========================================
# Lifespan with model service integration
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown with model service integration"""
    
    # Startup
    print(f"[+] D&D Game API starting...")
    print(f"[+] Model service URL: {MODEL_SERVER_URL}")
    
    try:
        # Access the API server instance
        api_server = app.state.game_server
        model_client = api_server.model_client
        
        if WAIT_FOR_MODELS:
            print("[+] Waiting for model service to be available...")
            if await model_client.wait_for_service(timeout=60.0):
                print("[+] ✅ Model service is available!")
                
                if AUTO_LOAD_MODELS:
                    print("[+] Auto-loading models...")
                    if await model_client.load_all_models():
                        print("[+] ✅ Models loaded successfully!")
                    else:
                        print("[-] ⚠️ Failed to load models, but service is available")
                else:
                    print("[+] Models not auto-loaded (set AUTO_LOAD_MODELS=true to enable)")
            else:
                print("[-] ⚠️ Model service not available - API will work but models may fail")
        else:
            print("[+] Not waiting for model service (set WAIT_FOR_MODELS=true to enable)")
        
        print(f"[+] ✅ D&D Game API ready!")
        
    except Exception as e:
        print(f"[-] Error during startup: {e}")
        print("[+] API will start anyway - models will auto-load on demand")
    
    # Yield control to the application
    yield
    
    # Shutdown
    print("[+] Shutting down D&D Game API...")
    try:
        api_server = app.state.game_server
        model_client = api_server.model_client
        model_client.close()
        print("[+] ✅ Cleanup complete.")
    except Exception as e:
        print(f"[-] Error during cleanup: {e}")

# ==========================================
# Create FastAPI app with model service
# ==========================================
app: FastAPI = create_server(
    model_server_url=MODEL_SERVER_URL,
    lifespan=lifespan
)

# ==========================================
# Development endpoints
# ==========================================
if os.getenv("DEV_MODE", "false").lower() == "true":
    
    @app.get("/dev/model-status")
    def dev_model_status():
        """Development endpoint to check model service status"""
        try:
            api_server = app.state.game_server
            model_client = api_server.model_client
            
            return {
                "model_servER_url": MODEL_SERVER_URL,
                "service_healthy": model_client.is_healthy(),
                "models_loaded": model_client.are_models_loaded(),
                "parser_ready": model_client.is_parser_ready(),
                "narrator_ready": model_client.is_narrator_ready(),
                "detailed_status": model_client.get_status()
            }
        except Exception as e:
            return {"error": str(e)}
    
    @app.post("/dev/load-models")
    def dev_load_models():
        """Development endpoint to manually load models"""
        try:
            api_server = app.state.game_server
            model_client = api_server.model_client
            
            success = model_client.load_all_models()
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @app.post("/dev/test-parse")
    def dev_test_parse(text: str = "I attack the goblin with my sword"):
        """Development endpoint to test parsing"""
        try:
            api_server = app.state.game_server  
            model_client = api_server.model_client
            
            result = model_client.parse_action(text)
            return {"text": text, "result": result}
        except Exception as e:
            return {"error": str(e)}

# ==========================================
# For development/testing
# ==========================================
if __name__ == "__main__":
    import uvicorn
    
    print(f"""
🎮 D&D Game API Server
=======================
Configuration:
- Model Server: {MODEL_SERVER_URL}
- Wait for models: {WAIT_FOR_MODELS}
- Auto-load models: {AUTO_LOAD_MODELS}

Environment Variables:
- MODEL_SERVER_URL=http://localhost:8001
- WAIT_FOR_MODELS=true|false
- AUTO_LOAD_MODELS=true|false  
- DEV_MODE=true (enables dev endpoints)

Make sure to start the model service first:
  python model_server.py --load-models
    """)
    
    uvicorn.run("backend.services.api.main:app", host="0.0.0.0", port=8000, reload=True)