"""
Model Service Client
Handles communication with the standalone model service.
Replaces direct ModelManager usage in the main API server.
"""

import time
import httpx
import asyncio
from typing import Optional, Dict, Any, List

from backend.models import (
    ParseActionResponse,
    ParseActionRequest,
    GenerateActionRequest,
    GenerateSceneRequest,
    GeneratedNarration,
    ParsedAction,
)


class AsyncModelServiceClient:
    """Async version of model service client"""

    def __init__(
        self, model_service_url: str = "http://localhost:8001", timeout: float = 30.0
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
        """Async version of parse_action"""
        try:
            response = await self.client.post(
                f"{self.base_url}/parse_action", json=request.model_dump()
            )
            response.raise_for_status()

            result_dict = response.json()
            return ParsedAction(**result_dict)

        except httpx.HTTPError as http_err:
            # This will be triggered if FastAPI raised HTTPException
            try:
                error_detail = response.json().get("detail", str(http_err))
            except Exception:
                error_detail = str(http_err)
            print(f"[CLIENT] Parse request failed: {error_detail}")
            return ParseActionResponse(action_type="unknown", details=error_detail)

        except Exception as e:
            print(f"[CLIENT] Parse request failed: {e}")
            return ParseActionResponse(action_type="unknown", details=str(e))

    async def generate_action(
        self, request: GenerateActionRequest
    ) -> GeneratedNarration:
        """Async version of generate_narration"""
        try:
            response = await self.client.post(
                f"{self.base_url}/generate_action", json=request.model_dump()
            )
            response.raise_for_status()

            result_dict = response.json()
            result = GeneratedNarration(**result_dict)

            return result

        except httpx.HTTPError as http_err:
            # This will be triggered if FastAPI raised HTTPException
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
        """Async version of generate_narration"""
        try:
            response = await self.client.post(
                f"{self.base_url}/generate_scene", json=request.model_dump()
            )
            response.raise_for_status()

            result_dict = response.json()
            result = GeneratedNarration(**result_dict)

            return result

        except httpx.HTTPError as http_err:
            # This will be triggered if FastAPI raised HTTPException
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
