import torch
from typing import Optional, Dict, Any, List
import gc
import re
import os
import json
from pathlib import Path

try:
    from llama_cpp import Llama

    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    print(
        "[-] llama-cpp-python not installed. Install with: pip install llama-cpp-python"
    )

from backend.game.core.interfaces import ActionNarrator
from backend.models import ParsedAction, ActionType, GenerateSceneRequest


class GGUFMistralNarrator(ActionNarrator):
    """GGUF Mistral-based D&D action narrator using llama-cpp-python"""

    def __init__(
        self,
        model_path: str = "/home/donovan/ai_models/ministral-8B-instruct-2410-gguf/Ministral-8B-Instruct-2410-Q4_K_M.gguf",
        n_gpu_layers: int = -1,  # -1 = offload all layers to GPU
        n_ctx: int = 4096,  # Context window
        verbose: bool = False,  # Disable verbose mode to stop flooding
    ):
        self.model_path = model_path
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx = n_ctx
        self.verbose = verbose

        self.model = None
        self._is_loaded = False

        # Check if CUDA is available
        self.cuda_available = torch.cuda.is_available()
        if not self.cuda_available:
            print("[!] CUDA not available, using CPU only")
            self.n_gpu_layers = 0

    def load_model(self) -> bool:
        """Load the GGUF model with llama-cpp-python"""
        if not LLAMA_CPP_AVAILABLE:
            print("[-] llama-cpp-python not available")
            return False

        try:
            print(f"[+] Loading GGUF Mistral narrator from {self.model_path}...")

            # Check if file exists
            if not os.path.exists(self.model_path):
                print(f"[-] Model file does not exist: {self.model_path}")
                return False

            # Show file info
            file_size = os.path.getsize(self.model_path) / (1024**3)
            print(f"[+] Model file size: {file_size:.2f} GB")

            # Check CUDA availability for llama-cpp-python
            try:
                test_model = Llama(model_path="", n_gpu_layers=1, verbose=False)
                cuda_available = True
                del test_model
            except:
                cuda_available = False

            if not cuda_available and self.n_gpu_layers > 0:
                print("[!] llama-cpp-python not compiled with CUDA support, using CPU")
                print(
                    "[!] To enable GPU: pip install llama-cpp-python --force-reinstall --no-cache-dir --config-settings cmake.define.LLAMA_CUBLAS=on"
                )
                self.n_gpu_layers = 0

            print(f"[+] Attempting to load with {self.n_gpu_layers} GPU layers...")

            # Load the GGUF model
            self.model = Llama(
                model_path=self.model_path,
                n_gpu_layers=self.n_gpu_layers,
                n_ctx=self.n_ctx,
                verbose=self.verbose,
                n_threads=8,  # Adjust based on your CPU cores
                n_batch=512,  # Batch size for prompt processing
            )

            self._is_loaded = True

            # Better device reporting
            if self.n_gpu_layers > 0:
                device_info = f"GPU ({self.n_gpu_layers} layers offloaded)"
                # Check if GPU memory actually increased
                if torch.cuda.is_available():
                    gpu_memory = torch.cuda.memory_allocated() / 1e9
                    print(f"[+] GPU memory after loading: {gpu_memory:.2f} GB")
            else:
                device_info = "CPU only"

            print(f"[+] GGUF Mistral narrator loaded successfully on {device_info}")
            return True

        except Exception as e:
            import traceback

            print(f"[-] Failed to load GGUF Mistral narrator: {e}")
            print(f"[-] Full traceback: {traceback.format_exc()}")
            self._is_loaded = False
            return False

    def unload_model(self) -> bool:
        """Unload the model to free resources"""
        try:
            if self.model:
                del self.model
                self.model = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            self._is_loaded = False
            print("[+] GGUF Mistral narrator unloaded successfully")
            return True
        except Exception as e:
            print(f"[-] Error unloading GGUF Mistral: {e}")
            return False

    def is_loaded(self) -> bool:
        return self._is_loaded and self.model is not None

    def generate_action_narration(
        self, action: ParsedAction, hit: bool, damage_type: str = "wound"
    ) -> str:
        if not self.is_loaded():
            print("[-] Narrator model not loaded")
            return f"{action.actor} performs {action.action}."

        try:
            input_prompt = self._create_input_prompt(action, hit, damage_type)

            # Debug the prompt if needed
            if self.verbose:
                print(f"[DEBUG] Input Prompt: {input_prompt}")

            raw_text = self._generate_text(input_prompt, max_tokens=64, temperature=0.6)

            # Check if generation failed
            if len(raw_text.strip()) < 5:
                print(f"[!] Generation failed, raw text: '{raw_text}'")
                return f"{action.actor} performs {action.action}."

            cleaned = self._clean_action_narration(
                raw_text, action.actor, action.target
            )

            if self.verbose:
                print(f"[DEBUG] Raw: '{raw_text}'")
                print(f"[DEBUG] Cleaned: '{cleaned}'")

            return cleaned
        except Exception as e:
            print(f"[-] Narration generation failed: {e}")
            import traceback

            print(f"[-] Full traceback: {traceback.format_exc()}")
            return f"{action.actor} performs {action.action}."

        # NOTE: parameters for this are not even close!

    def generate_scene_narration(self, request: GenerateSceneRequest):
        """Generate a scene description using the narrator model"""
        if not self.is_loaded():
            print("[-] Narrator model not loaded")
            return f"You find yourself in {request.scene.get('name', 'an unknown location')}."

        try:
            # Create the prompt for scene description
            scene_prompt = self._create_scene_prompt(request)
            print(scene_prompt)
            if self.verbose:
                print(f"[DEBUG] Scene prompt: {scene_prompt}")

            # Generate the scene description
            raw_text = self._generate_text(
                scene_prompt, max_tokens=200, temperature=0.6
            )

            # Clean and format the description
            # cleaned_description = self._clean_scene_description(raw_text, scene['name'], player['name'])
            cleaned_description = raw_text

            if self.verbose:
                print(f"[DEBUG] Raw scene: '{raw_text}'")
                print(f"[DEBUG] Cleaned scene: '{cleaned_description}'")

            return cleaned_description

        except Exception as e:
            print(f"[-] Scene description generation failed: {e}")
            import traceback

            print(f"[-] Full traceback: {traceback.format_exc()}")
            return f"You find yourself in {request.scene['name']}."

    def _create_input_prompt(
        self, action: ParsedAction, hit: bool, damage_type: str
    ) -> str:
        # Build the scenario description
        actor = action.actor
        target = action.target or "the target"
        action_desc = action.action

        # Add weapon if present and not already in action description
        if (
            action.weapon
            and action.action_type == ActionType.ATTACK
            and action.weapon not in action_desc
        ):
            action_desc = f"{action_desc} with {action.weapon}"
        elif action.weapon and action.action_type == ActionType.SPELL:
            action_desc = f"{action_desc} using {action.weapon}"

        # Build the base scenario
        if not hit:
            if action.action_type == ActionType.SPELL:
                scenario = f"{actor} tries to cast {action_desc} against {target} but the magic fails."
            elif action.action_type == ActionType.SOCIAL:
                scenario = f"{actor} attempts to {action_desc} with {target} but fails to persuade them."
            else:
                scenario = f"{actor} tries to {action_desc} against {target} but misses completely."
        else:
            if (
                action.action_type == ActionType.SPELL
            ):  # Will have to determine if spell type is an attack or not
                if damage_type == "kill":
                    scenario = f"{actor} unleashes devastating {action_desc} magic that proves fatal to {target}."
                elif damage_type == "critical":
                    scenario = f"{actor} casts powerful {action_desc} that severely affects {target}."
                else:
                    scenario = (
                        f"{actor} successfully casts {action_desc} against {target}."
                    )
            elif action.action_type == ActionType.SOCIAL:
                if damage_type == "outstanding_success":
                    scenario = f"{actor} completely wins over {target} with masterful {action_desc}."
                elif damage_type == "great_success":
                    scenario = f"{actor} effectively convinces {target} through skilled {action_desc}."
                else:
                    scenario = f"{actor} successfully uses {action_desc} to influence {target}."
            elif action.action_type == ActionType.ATTACK:
                if damage_type == "kill":
                    scenario = f"{actor} delivers a killing blow with {action_desc}, ending {target}'s life."
                elif damage_type == "critical":
                    scenario = f"{actor} lands a devastating {action_desc} that severely wounds {target}."
                else:
                    scenario = (
                        f"{actor} successfully strikes {target} with {action_desc}."
                    )
            else:
                scenario = f"{actor} successfully performs {action_desc}."

        # Add subject context if present
        subject_context = ""
        if action.subject:
            if action.action_type == ActionType.SOCIAL:
                subject_context = f" The topic is: {action.subject}."
            elif action.action_type == ActionType.SPELL:
                subject_context = f" The spell targets: {action.subject}."
            else:
                subject_context = f" Context: {action.subject}."

        # Add details if present
        details_context = ""
        if action.details:
            details_context = f" Additional details: {action.details}."

        # Build the full prompt
        full_scenario = scenario + subject_context + details_context

        # Balanced prompt with contextual information
        return f"""[INST] You are a skilled D&D dungeon master. 
            Write exactly one vivid sentence describing this scene. 
            Focus on sensory details and dynamic action. 
            No game mechanics or generic terms like "player" or "character".
            Use proper names if provided otherwise use pronouns.
            Do not use names not given.
            Speak in the third person.

            Scene: {full_scenario}

            One sentence description: [/INST]"""

    def _create_scene_prompt(self, request: GenerateSceneRequest):
        """Create the prompt for scene description generation"""
        # Load config from JSON file
        with open(
            "backend/game/parsers/narrator_parser/scene_prompt_conf.json", "r"
        ) as file:
            config = json.load(file)

        # Handle arrays by joining with newlines
        system_prompt_template = config["system_prompt"]
        if isinstance(system_prompt_template, list):
            system_prompt_template = "\n".join(system_prompt_template)

        # context_template = config["history"]
        # if isinstance(context_template, list):
        #     context_template = "\n".join(context_template)

        # Create context for template replacements
        context_data = {
            "scene": request.scene,
            "player": request.player,
        }

        return self._resolve_template(system_prompt_template, context_data)

    def _resolve_template(self, system_prompt_template: str, context_data: dict) -> str:
        """Resolve {var[key]} patterns in template"""

        def replacer(match):
            expr = match.group(1)  # Everything inside {}
            try:
                return str(eval(expr, {}, context_data))
            except:
                return match.group(0)  # Return original if can't resolve

        return re.sub(r"\{([^}]+)\}", replacer, system_prompt_template)

    def _generate_text(
        self, input: str, max_tokens: int = 64, temperature: float = 0.4
    ) -> str:
        try:
            # Generate with llama-cpp-python
            response = self.model(
                input,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                top_k=50,
                repeat_penalty=1.15,
                frequency_penalty=0.2,
                stop=["</s>", "[INST]", "[/INST]"],  # Stop tokens
                echo=False,  # Don't echo the prompt
            )

            # Extract the generated text
            generated_text = response["choices"][0]["text"]

            # Debug output
            if self.verbose or len(generated_text.strip()) < 5:
                print(f"[DEBUG] Generated text: '{generated_text.strip()}'")
                print(f"[DEBUG] Text length: {len(generated_text.strip())}")

            return generated_text.strip()

        except Exception as e:
            print(f"[-] Error in _generate_text: {e}")
            import traceback

            print(f"[-] Full traceback: {traceback.format_exc()}")
            return "The action occurs."

    def _clean_action_narration(
        self,
        text: str,
        actor_name: Optional[str] = None,
        target_name: Optional[str] = None,
    ) -> str:
        # Enhanced cleaning logic
        text = text.strip()

        # Remove common AI artifacts
        artifacts_to_remove = [
            r"^(Here\'s|Here is|I\'ll describe|Let me describe|Certainly|Of course).*?:",
            r"^(The scene unfolds as follows|Description).*?:",
            r"System:",
            r"User:",
            r"Assistant:",
            r"\*[^*]*\*",
            r"\{[^}]*\}",
            r"\[[^\]]*\]",
        ]
        for pattern in artifacts_to_remove:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
        text = text.strip()

        # Get the first good sentence
        sentences = re.split(r"[.!?]+", text)
        descriptive_sentence = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:
                skip_patterns = [
                    r"^(here|this|that|it|the scene)",
                    r"^(i will|i\'ll|let me|as requested)",
                    r"^(certainly|of course|indeed)",
                ]
                if not any(re.match(p, sentence, re.IGNORECASE) for p in skip_patterns):
                    descriptive_sentence = sentence
                    break

        if not descriptive_sentence:
            descriptive_sentence = "The action occurs as described."
        text = descriptive_sentence

        # ------------------------------
        # This will likely need to go away because actor will not always be player
        # ------------------------------
        # Enhanced name replacement - more aggressive pattern matching
        if actor_name and target_name:
            replacements = {
                r"\bplayer\b": actor_name,  # Most common issue
                r"\bcharacter\b": actor_name,
                r"\bhero\b": actor_name,
                r"\bprotagonist\b": actor_name,
                r"\badventurer\b": actor_name,
                r"\btarget\b": target_name,
                r"\benemy\b": target_name,
                r"\bfoe\b": target_name,
                r"\bopponent\b": target_name,
                r"\bthe player\b": actor_name,
                r"\bthe character\b": actor_name,
                r"\bthe hero\b": actor_name,
                r"\bthe target\b": target_name,
                r"\bthe enemy\b": target_name,
            }
            for pattern, replacement in replacements.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Clean up extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Capitalize first letter
        if text and text[0].islower():
            text = text[0].upper() + text[1:]

        # Ensure proper ending punctuation
        if text and text[-1] not in ".!?":
            text += "."

        # Length check - increased limit
        if len(text) < 5:  # or len(text) > 255:
            return f"{actor_name or 'The actor'} performs the action."

        return text

    # ------------------------------
    # Scene narration cleaner - temporary for now
    # ------------------------------
    def _clean_scene_description(self, text, scene_name, player_name):
        """Clean and format the generated scene description"""
        import re

        text = text.strip()

        # Remove common AI artifacts and instruction remnants
        artifacts_to_remove = [
            r"^(Here\'s|Here is|I\'ll describe|Let me describe|Certainly|Of course).*?:",
            r"^(The scene unfolds|Description).*?:",
            r"System:",
            r"User:",
            r"Assistant:",
            r"\[INST\]",
            r"\[\/INST\]",
            r"\*[^*]*\*",
            r"\{[^}]*\}",
            r"\[[^\]]*\]",
        ]
        for pattern in artifacts_to_remove:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
        text = text.strip()

        # Get the meaningful sentences
        sentences = re.split(r"[.!?]+", text)
        good_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:
                # Skip meta-commentary sentences
                skip_patterns = [
                    r"^(here|this describes|as a dm)",
                    r"^(i will|i\'ll|let me|as requested)",
                    r"^(certainly|of course|indeed)",
                    r"^(the description|this scene)",
                ]
                if not any(re.match(p, sentence, re.IGNORECASE) for p in skip_patterns):
                    good_sentences.append(sentence)

            # Stop after getting 2-3 good sentences
            if len(good_sentences) >= 3:
                break

        if not good_sentences:
            return f"You find yourself in {scene_name}."

        # Rejoin the sentences
        text = ". ".join(good_sentences)

        # Replace generic terms with proper names
        replacements = {
            r"\bplayer\b": player_name,
            r"\bcharacter\b": player_name,
            r"\bhero\b": player_name,
            r"\badventurer\b": player_name,
            r"\bprotagonist\b": player_name,
            r"\bthe player\b": player_name,
            r"\bthe character\b": player_name,
            r"\bthe hero\b": player_name,
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Ensure it starts with second person if it doesn't already
        if text and not re.match(r"^(You|Your)", text):
            # Try to convert third person to second person
            text = re.sub(r"^" + re.escape(player_name), "You", text)
            if not re.match(r"^(You|Your)", text):
                text = f"You find yourself here. {text}"

        # Ensure proper ending punctuation
        if text and text[-1] not in ".!?":
            text += "."

        # Capitalize first letter
        if text and text[0].islower():
            text = text[0].upper() + text[1:]

        # Length check
        if len(text) < 10:
            return f"You find yourself in {scene_name}."

        return text
