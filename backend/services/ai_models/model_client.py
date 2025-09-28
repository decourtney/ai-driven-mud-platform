"""
Model Service Client
Handles communication with the standalone model service.
Replaces direct ModelManager usage in the main API server.
"""

import time, json, websockets, httpx, asyncio
from typing import Optional, Dict, Any, List, AsyncGenerator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from backend.models import (
    ParsedAction,
    ParseActionRequest,
    GenerateActionRequest,
    GenerateSceneRequest,
    GeneratedNarration,
    ParsedAction,
    GenerateInvalidActionRequest,
    SceneExitRequest,
    SceneExitResult,
)


class AsyncModelServiceClient:
    """Async version of model service client"""

    def __init__(
        self, model_service_url: str = "http://localhost:8001", timeout: float = 45.0
    ):
        self.base_url = model_service_url.rstrip("/")
        self.timeout = timeout
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    # ==========================================
    # HEALTH & STATUS METHODS
    # ==========================================

    async def is_healthy(self) -> bool:
        """Check if model service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    async def get_status(self) -> Dict[str, Any]:
        """Get detailed model service status"""
        try:
            response = await self.client.get(f"{self.base_url}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "available": False}

    async def are_models_loaded(self) -> bool:
        """Check if all models are loaded"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                return data.get("models_loaded", False)
            return False
        except Exception:
            return False

    async def is_parser_ready(self) -> bool:
        """Check if parser model is ready"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                return data.get("parser_ready", False)
            return False
        except Exception:
            return False

    async def is_narrator_ready(self) -> bool:
        """Check if narrator model is ready"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                return data.get("narrator_ready", False)
            return False
        except Exception:
            return False

    async def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage from model service"""
        try:
            status = self.get_status()
            return status.get("memory", {})
        except Exception:
            return {}

    # ==========================================
    # MODEL MANAGEMENT METHODS
    # ==========================================

    async def load_all_models(self) -> bool:
        """Load all models on the model service"""
        try:
            print(f"[CLIENT] Requesting model loading from {self.base_url}...")
            response = await self.client.post(f"{self.base_url}/models/load")
            response.raise_for_status()

            result = response.json()
            success = result.get("success", False)

            if success:
                load_time = result.get("load_time_seconds", 0)
                print(f"[CLIENT] ✅ Models loaded successfully in {load_time:.2f}s")
            else:
                error = result.get("error", result.get("message", "Unknown error"))
                print(f"[CLIENT] ❌ Model loading failed: {error}")

            return success

        except Exception as e:
            print(f"[CLIENT] ❌ Error communicating with model service: {e}")
            return False

    async def unload_all_models(self) -> bool:
        """Unload all models on the model service"""
        try:
            response = await self.client.post(f"{self.base_url}/models/unload")
            response.raise_for_status()

            result = response.json()
            return result.get("success", False)

        except Exception as e:
            print(f"[CLIENT] Error unloading models: {e}")
            return False

    async def reload_models(self) -> bool:
        """Reload all models on the model service"""
        try:
            response = await self.client.post(f"{self.base_url}/models/reload")
            response.raise_for_status()

            result = response.json()
            return result.get("success", False)

        except Exception as e:
            print(f"[CLIENT] Error reloading models: {e}")
            return False

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    async def wait_for_service(
        self, timeout: float = 60.0, interval: float = 3.0
    ) -> bool:
        """Wait for model server to become available"""
        print(f"[CLIENT] Waiting for model server at {self.base_url}...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            if await self.is_healthy():
                print(f"[CLIENT] ✅ Model server is available!")
                return True

            print(f"[CLIENT] Model server not ready, retrying in {interval}s...")
            time.sleep(interval)

        print(f"[CLIENT] ❌ Model server did not become available within {timeout}s")
        return False

    async def ensure_models_loaded(self, auto_load: bool = True) -> bool:
        """Ensure models are loaded, optionally loading them if not"""
        if await self.are_models_loaded():
            return True

        if auto_load:
            print("[CLIENT] Models not loaded, attempting to load...")
            return await self.load_all_models()

        return False

    # ==========================================
    # MODEL INFERENCE METHODS
    # ==========================================

    async def parse_action(self, request: ParseActionRequest) -> ParsedAction:
        try:
            response = await self.client.post(
                f"{self.base_url}/parse_action",
                content=request.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result_dict = response.json()
            return ParsedAction(**result_dict)

        except httpx.HTTPError as http_err:
            try:
                error_detail = response.json().get("detail", str(http_err))
            except Exception:
                error_detail = str(http_err)
            print(f"[CLIENT] Parse request failed: {error_detail}")
            return ParsedAction(action_type="unknown", details=error_detail)

        except Exception as e:
            print(f"[CLIENT] Parse request failed: {e}")
            return ParsedAction(action_type="unknown", details=str(e))

    async def determine_scene_exit(self, request: SceneExitRequest) -> SceneExitResult:
        try:
            response = await self.client.post(
                f"{self.base_url}/determine_scene_exit",
                content=request.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result_dict = response.json()
            return SceneExitResult(**result_dict)

        except httpx.HTTPError as http_err:
            try:
                error_detail = response.json().get("detail", str(http_err))
            except Exception:
                error_detail = str(http_err)
            print(f"[CLIENT] Scene exit determination request failed: {error_detail}")
            return SceneExitResult(target_scene="unknown")

        except Exception as e:
            print(f"[CLIENT] Scene exit determination request failed: {e}")
            return SceneExitResult(target_scene="unknown")

    async def generate_action(
        self, request: GenerateActionRequest
    ) -> GeneratedNarration:
        try:
            response = await self.client.post(
                f"{self.base_url}/generate_action",
                content=request.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result_dict = response.json()

            # Ensure 'narration' is always present for Pydantic
            if "narration" not in result_dict or not result_dict["narration"]:
                result_dict["narration"] = ""

            return GeneratedNarration(**result_dict)

        except httpx.HTTPError as http_err:
            try:
                error_detail = response.json().get("detail", str(http_err))
            except Exception:
                error_detail = str(http_err)
            print(f"[CLIENT] Generation request failed: {error_detail}")
            return GeneratedNarration(action_type="unknown", details=error_detail)

        except Exception as e:
            print(f"[CLIENT] Generation request failed: {e}")
            return GeneratedNarration(action_type="unknown", details=str(e))

    async def generate_scene(self, request: GenerateSceneRequest) -> GeneratedNarration:
        try:
            response = await self.client.post(
                f"{self.base_url}/generate_scene",
                content=request.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result_dict = response.json()

            # Ensure 'narration' is always present for Pydantic
            if "narration" not in result_dict or not result_dict["narration"]:
                result_dict["narration"] = ""

            return GeneratedNarration(**result_dict)

        except httpx.HTTPError as http_err:
            try:
                error_detail = response.json().get("detail", str(http_err))
            except Exception:
                error_detail = str(http_err)
            print(f"[CLIENT] Generation request failed: {error_detail}")
            return GeneratedNarration(
                narration="", action_type="unknown", details=error_detail
            )

        except Exception as e:
            print(f"[CLIENT] Generation request failed: {e}")
            return GeneratedNarration(
                narration="", action_type="unknown", details=str(e)
            )

    async def generate_invalid_action(
        self, request: GenerateInvalidActionRequest
    ) -> GeneratedNarration:
        try:
            response = await self.client.post(
                f"{self.base_url}/generate_invalid_action",
                content=request.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result_dict = response.json()

            # Ensure 'narration' is always present for Pydantic
            if "narration" not in result_dict or not result_dict["narration"]:
                result_dict["narration"] = ""

            return GeneratedNarration(**result_dict)

        except httpx.HTTPError as http_err:
            try:
                error_detail = response.json().get("detail", str(http_err))
            except Exception:
                error_detail = str(http_err)
            print(f"[CLIENT] Generation request failed: {error_detail}")
            return GeneratedNarration(action_type="unknown", details=error_detail)

        except Exception as e:
            print(f"[CLIENT] Generation request failed: {e}")
            return GeneratedNarration(action_type="unknown", details=str(e))

    # NOTE: Dunno if this will ever get used
    async def batch_parse_actions(self, requests: List[ParseActionRequest]):
        """Parse multiple actions in one request (async)"""
        try:
            payload = [req.model_dump() for req in requests]

            response = await self.client.post(
                f"{self.base_url}/batch/parse", json=payload
            )
            response.raise_for_status()

            result = response.json()
            return result.get("results", [])

        except Exception as e:
            print(f"[CLIENT] Batch parse failed: {e}")
            return [{"action_type": "unknown", "error": str(e)} for _ in requests]

    # ==========================================
    # WEBSOCKET INFERENCE METHODS
    # ==========================================

    async def stream_scene_generation(
        self, request: GenerateSceneRequest
    ) -> AsyncGenerator[dict, None]:
        """Stream scene narration chunks from model_server WebSocket."""
        if self.base_url.startswith("https://"):
            ws_url = (
                self.base_url.replace("https://", "wss://") + "/ws/scene_generation"
            )
        else:
            ws_url = self.base_url.replace("http://", "ws://") + "/ws/scene_generation"

        print("\033[32m[MODEL_CLIENT]\033[0m Stream Scene Request:", request)
        print(f"\033[32m[MODEL_CLIENT]\033[0m WebSocket URL: {ws_url}")

        try:
            print(f"\033[32m[MODEL_CLIENT]\033[0m Attempting to connect to {ws_url}...")
            async with websockets.connect(ws_url) as ws:
                print(f"\033[32m[MODEL_CLIENT]\033[0m Connected successfully!")

                # Send the request
                request_json = request.model_dump_json()
                print(f"\033[32m[MODEL_CLIENT]\033[0m Sending request: {request_json}")
                await ws.send(request_json)
                print(
                    f"\033[32m[MODEL_CLIENT]\033[0m Request sent, waiting for messages..."
                )

                message_count = 0
                while True:
                    try:
                        # print(f"\033[32m[MODEL_CLIENT]\033[0m Waiting for message #{message_count + 1}...")
                        # Add timeout to prevent hanging
                        message = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        message_count += 1
                        # print(
                        #     f"[{time.time()}]\033[32m[MODEL_CLIENT]\033[0m Received message #{message_count}"
                        # )

                        try:
                            msg = json.loads(message)
                            # print(
                            #     f"[{time.time()}]\033[32m[MODEL_CLIENT]\033[0m Parsed message #{message_count}"
                            # )
                            yield msg

                            # Check for completion or error
                            if msg.get("type") == "done":
                                print(
                                    f"\033[32m[MODEL_CLIENT]\033[0m Stream completed normally after {message_count} messages"
                                )
                                break
                            elif msg.get("type") == "error":
                                print(
                                    f"\033[32m[MODEL_CLIENT]\033[0m Stream error: {msg.get('error')}"
                                )
                                break
                        except json.JSONDecodeError as json_error:
                            print(
                                f"\033[32m[MODEL_CLIENT]\033[0m Invalid JSON received: {message}, error: {json_error}"
                            )
                            continue

                    except asyncio.TimeoutError:
                        print(
                            f"\033[32m[MODEL_CLIENT]\033[0m Timeout waiting for message #{message_count + 1}, breaking"
                        )
                        break

                print(
                    f"\033[32m[MODEL_CLIENT]\033[0m Finished receiving {message_count} messages total"
                )

        except websockets.InvalidStatus as e:
            print(f"[WS] Connection failed with status: {e.status_code}")
            if hasattr(e, "response_headers"):
                print(f"[WS] Response headers: {e.response_headers}")
            raise
        except websockets.ConnectionClosed as e:
            print(f"[WS] Connection closed: code={e.code}, reason={e.reason}")
            raise
        except Exception as e:
            print(f"[WS] Unexpected error: {e}")
            import traceback

            print(f"[WS] Full traceback: {traceback.format_exc()}")
            raise
