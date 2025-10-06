#!/usr/bin/env python3
"""
Standalone Model Service
Runs AI models as a separate HTTP service for the D&D game engine.
This decouples models from the main API server for better scalability.
"""

import time, psutil, GPUtil, uvicorn, json, asyncio
from fastapi import FastAPI, HTTPException, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
from backend.services.ai_models.model_manager import ModelManager
from backend.services.api.models.health_models import HealthResponse
from backend.services.api.models.scene_models import (
    GeneratedNarration,
    GenerateSceneRequest,
)
from backend.services.api.models.action_models import (
    ParsedAction,
    ParseActionRequest,
    GenerateActionRequest,
    ParsedAction,
    GenerateInvalidActionRequest,
    TargetValidationRequest,
    TargetValidationResponse
)


class ModelServer:
    """Standalone model service for AI inference"""

    def __init__(self):
        self.model_manager = ModelManager()
        self.start_time = time.time()
        self.app = self._create_app()

    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get system memory usage"""
        try:
            # System memory
            memory = psutil.virtual_memory()

            # GPU memory (if available)
            gpu_info = []
            try:
                gpus = GPUtil.getGPUs()
                for gpu in gpus:
                    gpu_info.append(
                        {
                            "id": gpu.id,
                            "name": gpu.name,
                            "memory_used_mb": gpu.memoryUsed,
                            "memory_total_mb": gpu.memoryTotal,
                            "memory_percent": (gpu.memoryUsed / gpu.memoryTotal) * 100,
                            "utilization_percent": gpu.load * 100,
                        }
                    )
            except:
                gpu_info = []

            return {
                "system_memory_percent": memory.percent,
                "system_memory_used_gb": memory.used / (1024**3),
                "system_memory_total_gb": memory.total / (1024**3),
                "gpu_memory": gpu_info,
            }
        except Exception as e:
            return {"error": str(e)}

    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        app = FastAPI(
            title="D&D Model Service",
            version="1.0.0",
            description="Standalone AI model service for D&D game engine",
        )

        # CORS for local development
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # ==========================================
        # HEALTH & STATUS
        # ==========================================

        @app.get("/health", response_model=HealthResponse)
        def health_check():
            """Health check with detailed status"""
            return HealthResponse(
                status="healthy",
                models_loaded=self.model_manager.are_models_loaded(),
                parser_ready=self.model_manager.is_parser_ready(),
                narrator_ready=self.model_manager.is_narrator_ready(),
                memory_usage=self._get_memory_usage(),
                uptime_seconds=time.time() - self.start_time,
            )

        @app.get("/status")
        def detailed_status():
            """Detailed model status"""
            return {
                "service": "D&D Model Service",
                "uptime_seconds": time.time() - self.start_time,
                "models": {
                    "parser_loaded": self.model_manager.is_parser_ready(),
                    "narrator_loaded": self.model_manager.is_narrator_ready(),
                    "all_loaded": self.model_manager.are_models_loaded(),
                },
                "memory": self._get_memory_usage(),
                "model_paths": {
                    "parser": getattr(self.model_manager, "parser_model_path", None),
                    "narrator": getattr(
                        self.model_manager, "narrator_model_path", None
                    ),
                    "adapter": getattr(
                        self.model_manager, "narrator_adapter_path", None
                    ),
                },
            }

        # ==========================================
        # MODEL MANAGEMENT
        # ==========================================

        @app.post("/models/load")
        def load_models():
            """Load all models"""
            try:
                print("[MODEL] Loading models...")
                start_time = time.time()

                success = self.model_manager.load_all_models()
                load_time = time.time() - start_time

                if success:
                    print(f"[MODEL] ✅ Models loaded successfully in {load_time:.2f}s")
                    return {
                        "success": True,
                        "message": "Models loaded successfully",
                        "load_time_seconds": load_time,
                        "parser_ready": self.model_manager.is_parser_ready(),
                        "narrator_ready": self.model_manager.is_narrator_ready(),
                    }
                else:
                    print("[MODEL] ❌ Failed to load models")
                    return {
                        "success": False,
                        "message": "Failed to load models",
                        "load_time_seconds": load_time,
                    }

            except Exception as e:
                print(f"[MODEL] ❌ Error loading models: {e}")
                return {"success": False, "error": str(e)}

        @app.post("/models/unload")
        def unload_models():
            """Unload all models"""
            try:
                print("[MODEL] Unloading models...")
                self.model_manager.unload_all_models()
                print("[MODEL] ✅ Models unloaded successfully")
                return {"success": True, "message": "Models unloaded successfully"}
            except Exception as e:
                print(f"[MODEL] ❌ Error unloading models: {e}")
                return {"success": False, "error": str(e)}

        @app.post("/models/reload")
        def reload_models():
            """Reload all models"""
            try:
                print("[MODEL] Reloading models...")
                self.model_manager.unload_all_models()
                success = self.model_manager.load_all_models()

                if success:
                    print("[MODEL] ✅ Models reloaded successfully")
                    return {"success": True, "message": "Models reloaded successfully"}
                else:
                    print("[MODEL] ❌ Failed to reload models")
                    return {"success": False, "message": "Failed to reload models"}

            except Exception as e:
                print(f"[MODEL] ❌ Error reloading models: {e}")
                return {"success": False, "error": str(e)}

        # ==========================================
        # MODEL INFERENCE ENDPOINTS
        # ==========================================

        @app.post("/parse_action", response_model=ParsedAction)
        def parse_action(request: ParseActionRequest = Body(...)):
            """Parse player action using CodeLlama"""

            if not self.model_manager.is_parser_ready():
                # Try to auto-load
                print("[MODEL] Parser not ready, attempting to load...")
                if not self.model_manager.load_all_models():
                    raise HTTPException(
                        status_code=503, detail="Parser model not available"
                    )
            try:
                return self.model_manager.parse_action(request)

            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Parse failed: {e}")

        @app.post("/determine_valid_target", response_model=TargetValidationResponse)
        def determine_valid_target(request: TargetValidationRequest = Body(...)):
            """Determine what the actor is targeting"""

            if not self.model_manager.is_parser_ready():
                # Try to auto-load
                print("[MODEL] Parser not ready, attempting to load...")
                if not self.model_manager.load_all_models():
                    raise HTTPException(
                        status_code=503, detail="Parser model not available"
                    )
            try:
                return self.model_manager.determine_valid_target(request)

            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Determine target failed: {e}"
                )

        @app.post("/generate_action", response_model=GeneratedNarration)
        def generate_action_narration(request: GenerateActionRequest):
            """Generate narrative telling of the players action"""
            if not self.model_manager.is_narrator_ready():
                # Try to auto-load
                print("[MODEL] Narrator not ready, attempting to load...")
                if not self.model_manager.load_all_models():
                    raise HTTPException(
                        status_code=503, detail="Narrator model not available"
                    )

            try:
                narration = self.model_manager.generate_action_narration(request)

                return GeneratedNarration(narration=narration)

            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Generate action failed: {e}"
                )

        @app.post("/generate_scene", response_model=GeneratedNarration)
        def generate_scene_narration(request: GenerateSceneRequest):
            """Generate narration"""
            if not self.model_manager.is_narrator_ready():
                # Try to auto-load
                print("[MODEL] Narrator not ready, attempting to load...")
                if not self.model_manager.load_all_models():
                    raise HTTPException(
                        status_code=503, detail="Narrator model not available"
                    )

            try:
                narration = self.model_manager.generate_scene_narration(request)

                return GeneratedNarration(narration=narration)

            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Generate scene failed: {e}"
                )

        @app.post("/generate_invalid_action", response_model=GeneratedNarration)
        def generate_invalid_action(request: GenerateInvalidActionRequest):
            """Generate narration of invalid user action... for flavor?"""
            if not self.model_manager.is_narrator_ready():
                # Try to auto-load
                print("[MODEL] Narrator not ready, attempting to load...")
                if not self.model_manager.load_all_models():
                    raise HTTPException(
                        status_code=503, detail="Narrator model not available"
                    )

            try:
                narration = self.model_manager.generate_invalid_action_narration(
                    request
                )

                return GeneratedNarration(narration=narration)

            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Generate invalid action failed: {e}"
                )

        # ==========================================
        # WEBSOCKET INFERENCE METHODS
        # ==========================================

        @app.websocket("/ws/scene_generation")
        async def ws_scene_generation(websocket: WebSocket):
            print(f"\033[34m[MODEL_SERVER]\033[0m New WebSocket connection from {websocket.client}")
            await websocket.accept()
            print("\033[34m[MODEL_SERVER]\033[0m WebSocket connection accepted")

            try:
                # Receive the request data
                # print("\033[34m[MODEL_SERVER]\033[0m Waiting for request data...")
                data = await websocket.receive_text()
                # print(f"\033[34m[MODEL_SERVER]\033[0m Received data: {data}")

                request_dict = json.loads(data)
                # print(f"\033[34m[MODEL_SERVER]\033[0m Parsed request: {request_dict}")

                # Convert to GenerateSceneRequest object
                request = GenerateSceneRequest(**request_dict)
                # print(f"\033[34m[MODEL_SERVER]\033[0m Created request object: {request}")

                # Ensure narrator ready (sync calls, not async)
                if not self.model_manager.is_narrator_ready():
                    print("\033[34m[MODEL_SERVER]\033[0m Narrator not ready, attempting to load models...")
                    loaded = self.model_manager.load_all_models()
                    if not loaded:
                        error_msg = {"type": "error", "error": "Narrator not ready"}
                        print(f"\033[34m[MODEL_SERVER]\033[0m Sending error: {error_msg}")
                        await websocket.send_json(error_msg)
                        await websocket.close()
                        return

                try:
                    # Check if your model_manager has an async streaming method
                    if hasattr(self.model_manager, "stream_scene_narration"):
                        # print("\033[34m[MODEL_SERVER]\033[0m Starting streaming generation...")

                        chunk_count = 0
                        # Stream from model
                        async for chunk in self.model_manager.stream_scene_narration(request):
                            chunk_count += 1
                            # print(
                            #     f"\033[34m[MODEL_SERVER]\033[0m Processing chunk #{chunk_count}: {type(chunk)} - {chunk}"
                            # )

                            # Ensure chunk is serializable
                            if hasattr(chunk, "model_dump"):
                                chunk_data = chunk.model_dump()
                            elif isinstance(chunk, dict):
                                chunk_data = chunk
                            else:
                                # Convert to dict if it's not already
                                chunk_data = {"narration": str(chunk)}

                            message_to_send = {"type": "chunk", "data": chunk_data}
                            # print(f"\033[34m[MODEL_SERVER]\033[0m Sending message: {message_to_send}")

                            try:
                                await websocket.send_json(message_to_send)
                                await asyncio.sleep(0)
                                # print(
                                #     f"[{time.time()}]\033[34m[MODEL_SERVER]\033[0m Successfully sent chunk #{chunk_count}"
                                # )
                            except Exception as send_error:
                                print(f"\033[34m[MODEL_SERVER]\033[0m Error sending chunk #{chunk_count}: {send_error}")
                                break

                        print(f"\033[34m[MODEL_SERVER]\033[0m Finished processing {chunk_count} chunks")

                    else:
                        print("\033[34m[MODEL_SERVER]\033[0m Streaming not available, using fallback...")
                        # Fallback to regular generation if streaming not available
                        narration = self.model_manager.generate_scene_narration(request)
                        fallback_msg = {"type": "chunk", "data": {"narration": narration}}
                        print(f"\033[34m[MODEL_SERVER]\033[0m Sending fallback: {fallback_msg}")
                        await websocket.send_json(fallback_msg)

                    # Send completion signal
                    done_msg = {"type": "done"}
                    print(f"\033[34m[MODEL_SERVER]\033[0m Sending completion signal: {done_msg}")
                    await websocket.send_json(done_msg)
                    print("\033[34m[MODEL_SERVER]\033[0m Streaming complete, done signal sent")

                except Exception as e:
                    print(f"\033[34m[MODEL_SERVER]\033[0m Error during generation: {e}")
                    import traceback

                    print(f"\033[34m[MODEL_SERVER]\033[0m Full traceback: {traceback.format_exc()}")

                    try:
                        error_msg = {"type": "error", "error": str(e)}
                        print(f"\033[34m[MODEL_SERVER]\033[0m Sending error message: {error_msg}")
                        await websocket.send_json(error_msg)
                    except:
                        print("\033[34m[MODEL_SERVER]\033[0m Failed to send error message - WebSocket might be closed")

            except WebSocketDisconnect:
                print("\033[34m[MODEL_SERVER]\033[0m Client disconnected")
            except json.JSONDecodeError as e:
                print(f"\033[34m[MODEL_SERVER]\033[0m Invalid JSON received: {e}")
                try:
                    await websocket.send_json({"type": "error", "error": "Invalid JSON"})
                    await websocket.close()
                except:
                    pass
            except Exception as e:
                print(f"\033[34m[MODEL_SERVER]\033[0m Unexpected error: {e}")
                import traceback

                print(f"\033[34m[MODEL_SERVER]\033[0m Full traceback: {traceback.format_exc()}")

                try:
                    await websocket.send_json({"type": "error", "error": str(e)})
                    await websocket.close()
                except:
                    pass
            finally:
                print("\033[34m[MODEL_SERVER]\033[0m WebSocket connection cleanup complete")

        # ==========================================
        # BATCH ENDPOINTS (for efficiency)
        # ==========================================

        # @app.post("/batch/parse_actions")
        # def batch_parse_actions(requests: List[ParseActionRequest]):
        #     """Parse multiple actions in one request"""
        #     if not self.model_manager.is_parser_ready():
        #         raise HTTPException(
        #             status_code=503, detail="Parser model not available"
        #         )

        #     results = []
        #     for req in requests:
        #         try:
        #             result = self.model_manager.parse_action(
        #                 req.text, context=req.context
        #             )
        #             results.append(
        #                 ParsedAction(
        #                     success=True,
        #                     action_type=result.get("action_type", "unknown"),
        #                     target=result.get("target"),
        #                     damage_roll=result.get("damage_roll"),
        #                     difficulty=result.get("difficulty"),
        #                 )
        #             )
        #         except Exception as e:
        #             results.append(
        #                 ParsedAction(success=False, action_type="error", error=str(e))
        #             )

        #     return {"results": results}

        return app

    def run(self, host: str = "0.0.0.0", port: int = 8001):
        """Run the model service"""
        print(
            f"""
🤖 D&D Model Service Starting
===============================
- Host: {host}:{port}
- Endpoints:
  • GET  /health            (health check)
  • GET  /status            (detailed status) 
  • POST /models/load       (load models)
  • POST /models/unload     (unload models)
  • POST /parse_action      (parse actions)
  • POST /generate_action   (generate narration)
  • POST /generate_scene    (generate narration)
  • POST /batch/parse       (batch parsing)

Ready for API server connections!
        """
        )

        uvicorn.run(self.app, host=host, port=port)


# ==========================================
# CLI INTERFACE
# ==========================================


def main():
    """CLI interface for model service"""
    import argparse

    parser = argparse.ArgumentParser(description="D&D Model Service")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind to")
    parser.add_argument(
        "--load-models", action="store_true", help="Load models at startup"
    )

    args = parser.parse_args()

    service = ModelServer()

    # Load models at startup if requested
    if args.load_models:
        print("[STARTUP] Loading models at startup...")
        service.model_manager.load_all_models()

    service.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
