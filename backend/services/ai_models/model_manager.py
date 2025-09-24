import torch

from typing import Optional, Dict, List, Any

from backend.game.core.interfaces import ActionParser, ActionNarrator
from backend.models import (
    ParsedAction,
    ValidationResult,
    GenerateSceneRequest,
    ParseActionRequest,
    GenerateActionRequest,
)
from backend.game.parsers.action_parser.codellama_parser import CodeLlamaParser
from backend.game.parsers.narrator_parser.mistral_narrator import GGUFMistralNarrator


class ModelManager:
    def __init__(
        self,
        parser_model_path: Optional[str] = None,
        narrator_model_path: Optional[str] = None,
        narrator_adapter_path: Optional[str] = None,
    ):
        # Create actual instances, not class references
        self.parser = (
            CodeLlamaParser(parser_model_path)
            if parser_model_path
            else CodeLlamaParser()
        )
        self.narrator = (
            GGUFMistralNarrator(narrator_model_path)
            if narrator_model_path
            else GGUFMistralNarrator()
        )
        self.models_loaded = False

    def load_all_models(self) -> bool:
        """Load both models at startup"""
        if self.models_loaded:
            return True

        try:
            print("[+] Loading Narrator model...")
            if not self.narrator.load_model():
                raise RuntimeError("Failed to load narrator")
            print(
                f"[+] Narrator loaded - GPU usage: {torch.cuda.memory_allocated() / 1024**3:.2f} GB"
            )

            print("[+] Loading Action parser...")
            if not self.parser.load_model():
                raise RuntimeError("Failed to load parser")
            print(
                f"[+] Parser loaded - GPU usage: {torch.cuda.memory_allocated() / 1024**3:.2f} GB"
            )

            self.models_loaded = True
            return True

        except Exception as e:
            print(f"[-] Error loading models: {e}")
            self.models_loaded = False
            return False

    def is_parser_ready(self) -> bool:
        """Check if parser is loaded and ready"""
        return self.parser is not None and self.parser.is_loaded()

    def is_narrator_ready(self) -> bool:
        """Check if narrator is loaded and ready"""
        return self.narrator is not None and self.narrator.is_loaded()

    def are_models_loaded(self) -> bool:
        """Check if both models are loaded"""
        return self.is_parser_ready() and self.is_narrator_ready()

    def parse_action(self, request: ParseActionRequest) -> ParsedAction:
        """Process user input - no loading/unloading needed"""
        if not self.is_parser_ready():
            if not self.load_all_models():
                raise RuntimeError("Failed to load models")
        return self.parser.parse_action(request)

    # change this signature to accept request: GenerateActionRequest then adjust model
    def generate_action_narration(self, request: GenerateActionRequest) -> str:
        """Generate narration response - no loading/unloading needed"""
        if not self.is_narrator_ready():
            if not self.load_all_models():
                raise RuntimeError("Failed to load models")
        return self.narrator.generate_action_narration(request)

    def generate_scene_narration(self, request: GenerateSceneRequest) -> str:
        """Generate scene description - no loading/unloading needed"""
        if not self.is_narrator_ready():
            if not self.load_all_models():
                raise RuntimeError("Failed to load models")
        return self.narrator.generate_scene_narration(request)

    def generate_invalid_action_narration(
        self, validation_result: ValidationResult
    ) -> str:
        """Generate narration for invalid action"""
        if not self.is_narrator_ready():
            if not self.load_all_models():
                raise RuntimeError("Failed to load models")
        return "Invalid action"  # Temporary placeholder
        return self.narrator.generate_invalid_action_narration(validation_result)

    def get_memory_usage(self) -> dict:
        """Get current GPU memory usage"""
        if torch.cuda.is_available():
            return {
                "allocated_gb": torch.cuda.memory_allocated() / 1024**3,
                "reserved_gb": torch.cuda.memory_reserved() / 1024**3,
                "device": torch.cuda.get_device_name(),
            }
        return {"error": "CUDA not available"}

    def unload_all_models(self):
        """Only call this when shutting down completely"""
        if self.parser:
            self.parser.unload_model()
        if self.narrator:
            self.narrator.unload_model()
        torch.cuda.empty_cache()
        self.models_loaded = False
        print("[+] All models unloaded")
