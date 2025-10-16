"""
CodeLlama-based action parser implementing the ActionParser interface.
This can now be easily swapped out or mocked for testing.
"""

import torch, re, json, gc
from typing import List, Any, Dict
from difflib import SequenceMatcher
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    StoppingCriteria,
    StoppingCriteriaList,
)
from backend.services.api.models.scene_models import SceneExitRequest, SceneExitResult
from backend.services.api.models.action_models import (
    ParsedAction,
    ActionType,
    ParseActionRequest,
    TargetValidationRequest,
    TargetValidationResponse,
)


PROMPT_CONF_PATH = "backend/parsers/action_parser/prompts"


class StopOnStrings(StoppingCriteria):
    def __init__(self, stop_strings, tokenizer):
        self.tokenizer = tokenizer
        self.stop_sequences = [
            tokenizer(s, return_tensors="pt").input_ids.squeeze() for s in stop_strings
        ]

    def __call__(self, input_ids, scores, **kwargs):
        for stop_seq in self.stop_sequences:
            if len(input_ids[0]) >= len(stop_seq):
                if input_ids[0, -len(stop_seq) :].tolist() == stop_seq.tolist():
                    return True
        return False


class CodeLlamaParser:
    """CodeLlama-based natural language action parser"""

    def __init__(
        self, model_path: str = "/home/donovan/ai_models/codellama-7b-instruct-hf"
    ):
        self.model_path = model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None
        self._is_loaded = False
        self.bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

        # Fallback parser for when CodeLlama fails
        self.fallback_parser = None

    def load_model(self) -> bool:
        """Load the CodeLlama model and tokenizer"""
        try:
            print(f"[+] Loading CodeLlama parser from {self.model_path}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                quantization_config=self.bnb_config,
            )

            self._is_loaded = True
            print(f"[+] CodeLlama parser loaded on {self.device}")
            return True

        except Exception as e:
            print(f"[-] Failed to load CodeLlama parser: {e}")
            self._is_loaded = False
            return False

    def unload_model(self) -> bool:
        """Unload the model to free GPU/CPU resources"""
        try:
            if self.model is not None:
                del self.model
            if self.tokenizer is not None:
                del self.tokenizer

            self.model = None
            self.tokenizer = None

            gc.collect()

            # Clear GPU cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.ipc_collect()
                torch.cuda.synchronize()

            self._is_loaded = False

            print("[+] Parser unloaded successfully")
            return True
        except Exception as e:
            print(f"[-] Error unloading CodeLlama: {e}")
            return False

    def is_loaded(self) -> bool:
        """Check if parser is ready to use"""
        return self._is_loaded and self.model is not None

    def parse_action(self, request: ParseActionRequest) -> ParsedAction:
        """Parse natural language input into structured action"""
        print("[DEBUG] Starting parse_action with request:", request)

        if not self.is_loaded():
            print("[-] CodeLlama not loaded, using fallback parser")
            fallback_result = self.fallback_parser.parse_action(request.action)
            # Handle fallback result and add actor_type
            if isinstance(fallback_result, dict):
                fallback_result["actor_type"] = request.actor_type
                return ParsedAction(**fallback_result)
            else:
                result_dict = fallback_result.model_dump()
                result_dict["actor_type"] = request.actor_type
                return ParsedAction(**result_dict)

        try:
            print("[DEBUG] CodeLlama is loaded, proceeding with parsing")

            # Prepare input
            actor = request.actor
            actor_type = request.actor_type
            action = request.action.strip()
            prompt = self.create_action_parse_prompt(actor, actor_type, action)
            print(f"[DEBUG] Raw action: '{request}'")

            response = self.generate_from_model(prompt)
            print(f"[DEBUG] Model response: '{response}'")

            # Parse the response
            parsed_result = self.parse_llama_response(response, action)
            print("[DEBUG] Parse result:", parsed_result)

            # Add actor_type
            parsed_result["actor_type"] = actor_type
            print("[DEBUG] Result dict with actor_type:", parsed_result)

            # Create and return ParsedAction
            final_result = ParsedAction(**parsed_result)
            print("[DEBUG] Final ParsedAction created:", final_result)
            return final_result

        except Exception as e:
            print(f"[-] CodeLlama parsing failed: {e}, using fallback")
            fallback_result = self.fallback_parser.parse_action(request.action)

            # Handle fallback result and add actor_type
            if isinstance(fallback_result, dict):
                fallback_result["actor_type"] = request.actor_type
                return ParsedAction(**fallback_result)
            else:
                result_dict = fallback_result.model_dump()
                result_dict["actor_type"] = request.actor_type
                return ParsedAction(**result_dict)

    def create_action_parse_prompt(
        self, actor: str, actor_type: str, action: str
    ) -> str:
        """Create a well-structured prompt for CodeLlama"""
        # Load config from JSON file
        with open(f"{PROMPT_CONF_PATH}/action_parse_prompt.json", "r") as file:
            system_prompt = json.load(file)

        return f"""{system_prompt}
        Actor: "{actor}"
        Actor Type: "{actor_type}"
        Input: "{action}"
        Output: """

    # NOTE: May need to adjust generation parameters for best results
    def generate_from_model(self, prompt: str, max_tokens=80) -> str:
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=1024,
            truncation=True,
            padding=True,
        )
        if self.device == "cuda":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

        stopping_criteria = self.make_stop_criteria(["===END==="], self.tokenizer)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=0.1,
                top_p=0.9,
                # top_k=50,
                # repetition_penalty=1.2,
                # length_penalty=1.0,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                stopping_criteria=stopping_criteria,
            )

        decoded = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
        ).strip()

        stop_strings = ["===END==="]  # or however many you use
        for stop in stop_strings:
            idx = decoded.find(stop)
            if idx != -1:
                decoded = decoded[:idx].strip()
                break

        return decoded

    def make_stop_criteria(self, stop_strings, tokenizer):
        return StoppingCriteriaList([StopOnStrings(stop_strings, tokenizer)])

    def parse_llama_response(self, response: str, original_input: str) -> dict:
        """Parse the CodeLlama model's JSON response into a dict structure."""

        response = response.strip()

        # Truncate at known stop markers
        stop_marker = "===END==="
        if stop_marker in response:
            response = response.split(stop_marker, 1)[0].strip()

        # Extract first JSON object from response
        json_match = re.search(r"\{.*?\}", response, re.DOTALL)
        if not json_match:
            print("[-] No JSON object found in model output.")
            return self._fallback_to_dict(original_input)

        json_str = json_match.group(0)

        # Clean common issues before parsing
        json_str = re.sub(r",\s*}", "}", json_str)  # remove trailing commas
        json_str = re.sub(r",\s*]", "]", json_str)
        json_str = json_str.replace("“", '"').replace("”", '"').replace("’", "'")

        try:
            parsed_json = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[-] JSON parsing failed: {e}")
            return self._fallback_to_dict(original_input)

        # Normalize & fill defaults
        return {
            "actor": parsed_json.get("actor", "player"),
            "action": parsed_json.get("action", "unknown action"),
            "target": parsed_json.get("target"),
            "action_type": self._normalize_action_type(
                parsed_json.get("action_type", "INTERACT")
            ),
            "weapon": parsed_json.get("weapon"),
            "subject": parsed_json.get("subject"),
            "details": parsed_json.get("details"),
        }

    def _fallback_to_dict(self, original_input: str) -> dict:
        """Use fallback parser and ensure consistent dict output."""
        print(f"[-] CodeLlama response invalid, using fallback for: '{original_input}'")
        fallback_result = self.fallback_parser.parse_action(original_input)
        return (
            fallback_result
            if isinstance(fallback_result, dict)
            else fallback_result.model_dump()
        )

    # def parse_llama_response(
    #     self, response: str, original_input: str
    # ) -> dict:  # Return dict, not ParsedAction
    #     """Parse the CodeLlama model's JSON response"""
    #     # Clean up response
    #     response = response.strip()
    #     # Remove trailing text
    #     stop_patterns = [r"===END==="]
    #     for pattern in stop_patterns:
    #         match = re.search(pattern, response)
    #         if match:
    #             response = response[: match.start()]
    #             break

    #     # Extract JSON
    #     json_patterns = [
    #         r'\{[^{}]*"actor"[^{}]*\}',
    #         r'\{[^{}]*"action"[^{}]*\}',
    #         r"\{.*?\}",
    #     ]

    #     json_str = None
    #     for pattern in json_patterns:
    #         json_match = re.search(pattern, response, re.DOTALL)
    #         if json_match:
    #             json_str = json_match.group(0)
    #             break

    #     if json_str:
    #         try:
    #             # Fix common JSON issues
    #             # json_str = json_str.replace("'", '"')
    #             json_str = re.sub(r",\s*}", "}", json_str)
    #             parsed_json = json.loads(json_str)

    #             # Return dict instead of ParsedAction
    #             return {
    #                 "actor": parsed_json.get("actor", "player"),
    #                 "action": parsed_json.get("action", "unknown action"),
    #                 "target": parsed_json.get("target"),
    #                 "action_type": self._normalize_action_type(
    #                     parsed_json.get("action_type", "INTERACT")
    #                 ),
    #                 "weapon": parsed_json.get("weapon"),
    #                 "subject": parsed_json.get("subject"),
    #                 "details": parsed_json.get("details"),
    #                 # Don't include actor_type here - it will be added in parse_action
    #             }
    #         except (json.JSONDecodeError, ValueError) as e:
    #             print(f"[-] JSON parsing failed: {e}")

    #     # Fall back to fallback parser result
    #     print(f"[-] CodeLlama response invalid, using fallback for: '{original_input}'")
    #     fallback_result = self.fallback_parser.parse_action(original_input)

    #     # Convert fallback result to dict
    #     if isinstance(fallback_result, dict):
    #         return fallback_result
    #     else:
    #         return fallback_result.model_dump()

    def _normalize_action_type(self, action_type: str) -> str:
        """Normalize action type to valid ActionType values"""
        if action_type is None:
            return "INTERACT"

        action_type = action_type.upper()

        if action_type in [e.value for e in ActionType]:
            return action_type

        # Map common variations
        type_mappings = {
            "combat": "ATTACK",
            "magic": "SPELL",
            "talk": "SOCIAL",
            "conversation": "SOCIAL",
            "move": "MOVEMENT",
            "use": "INTERACT",
            "object": "INTERACT",
        }

        return type_mappings.get(action_type, "INTERACT")

    # -------------------------------------------------------------------------------------------
    # Scene exit determination methods
    # -------------------------------------------------------------------------------------------

    def determine_valid_target(
        self, request: TargetValidationRequest
    ) -> TargetValidationResponse:
        if not self.is_loaded():
            raise RuntimeError("CodeLlama parser not loaded")
        candidates = request.candidates
        query = request.query.strip()

        prompt = self.create_scene_exit_prompt(query, candidates)
        # print("\033[91m[DEBUG]\033[0m LLM Validator Prompt:", prompt)

        response = self.generate_from_model(prompt).strip("`").strip()

        # best_match = response if response != "" else "none"
        best_match = next(
            (d for d in candidates if d["name"].replace("_", " ") == response), None
        )

        if not best_match:
            print(
                "\n\033[96m[LLM MATCH]\033[0m: None",
                "\n",
            )
            return TargetValidationResponse(target=best_match)

        print(
            "\n\033[96m[LLM MATCH]\033[0m:",
            best_match["name"].replace("_", " "),
            "\n",
        )

        candidate_names = {e["name"]: e for e in candidates}
        print("\033[91m[DEBUG]\033[0m Available targets:", list(candidate_names.keys()))

        # Token/Sequence verification
        if best_match["name"] in candidate_names:

            # Compute similarity
            sim = max(
                # self.token_similarity(target, match_label),
                self.token_similarity(query, best_match["name"].replace("_", " ")),
                # self.sequence_similarity(target, match_label),
                self.sequence_similarity(query, best_match["name"].replace("_", " ")),
            )
            print(
                f"[DEBUG] Similarity between '{query}' and '{best_match["name"].replace("_", " ")}': {sim:.2f}"
            )

            #########################################
            #                                       #
            #      sim threshold can be tuned       #
            #                                       #
            #########################################
            if sim < 0.50:
                best_match = None

        else:
            # If model gave something invalid, fallback to none
            best_match = None

        return TargetValidationResponse(target=best_match)

    def normalize_string(self, text: str) -> list[str]:
        """Lowercase, remove punctuation, split into words, remove stopwords."""
        STOPWORDS = {"to", "the", "a", "an", "run", "walk", "go", "move", "goto"}
        text = re.sub(r"[^\w\s]", "", text.lower())
        words = text.split()
        return [w for w in words if w not in STOPWORDS]

    def token_similarity(self, a: str, b: str) -> float:
        set_a = set(self.normalize_string(a))
        set_b = set(self.normalize_string(b))
        ts = len(set_a & set_b) / len(set_a | set_b) if set_a or set_b else 0.0
        print("\033[94m[LLM Token:]\033[0m ", ts)
        return ts

    def sequence_similarity(self, a: str, b: str) -> float:
        """Fallback: fuzzy string ratio."""
        sm = SequenceMatcher(None, a.lower(), b.lower()).ratio()
        print("\033[94m[LLM Sequence:]\033[0m ", sm)
        return sm

    def create_scene_exit_prompt(
        self, query: str, candidates: List[Dict[str, Any]]
    ) -> str:
        # Load prompt template from JSON
        with open(f"{PROMPT_CONF_PATH}/scene_exit_prompt.json", "r") as f:
            prompts = json.load(f)
        template = "\n".join(prompts["system_prompt"])

        # Build exits string
        candidates_str = "\n".join(
            f"Name = {e['name'].replace('_', ' ')}: Label = {e['label']}"
            for e in candidates
        )
        # Fill template
        prompt = template.format(query=query, candidates=candidates_str)
        return prompt
