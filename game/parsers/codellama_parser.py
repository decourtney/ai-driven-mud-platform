"""
CodeLlama-based action parser implementing the ActionParser interface.
This can now be easily swapped out or mocked for testing.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import json
import re
from typing import Dict, Optional
import gc

from game.core.interfaces import ActionParser
from game.core.models import ParsedAction, ActionType
from game.parsers.fallback_parser import FallbackParser


class CodeLlamaParser(ActionParser):
    """CodeLlama-based natural language action parser"""
    
    def __init__(self, model_path: str = "/home/donovan/ai_models/codellama-7b-instruct-hf"):
        self.model_path = model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None
        self._is_loaded = False
        self.bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )
        
        # Fallback parser for when CodeLlama fails
        self.fallback_parser = FallbackParser()
        
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
                quantization_config=self.bnb_config
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
    
    def parse_action(self, user_input: str) -> ParsedAction:
        """Parse natural language input into structured action"""
        if not self.is_loaded():
            print("[-] CodeLlama not loaded, using fallback parser")
            return self.fallback_parser.parse_action(user_input)
        
        try:
            return self._parse_with_llama(user_input)
        except Exception as e:
            print(f"[-] CodeLlama parsing failed: {e}, using fallback")
            return self.fallback_parser.parse_action(user_input)
    
    def _parse_with_llama(self, user_input: str) -> ParsedAction:
        """Internal method to parse using CodeLlama"""
        cleaned_input = user_input.strip()
        cleaned_input = re.sub(r'\bInput:\s*', '', cleaned_input)
        
        prompt = self._create_prompt(cleaned_input)
        
        # Tokenize and generate
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=1024,
            truncation=True,
            padding=True
        )
        
        # Move ALL inputs to the same device as model
        if self.device == "cuda":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            try:
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=80,
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    tokenizer=self.tokenizer,
                    stop_strings=["\n\nInput:", "Input:", "\n\n", "Output:", "\nInput"]
                )
            except:
                # Fallback without stop_strings if not supported
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=80,
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
        
        # Decode response
        response = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:], 
            skip_special_tokens=True
        ).strip()
        
        return self._parse_llama_response(response, cleaned_input)
    
    def _create_prompt(self, user_input: str) -> str:
        """Create a well-structured prompt for CodeLlama"""
        system_prompt = """
            You are a D&D text action parser.
            Given user input, return a JSON object with these keys:

            - Fields: "actor", "action", "target", "action_type", "weapon", "subject", "details".
            - actor: who/what is performing the action.
            - action: verb or short phrase describing what the actor is doing.
            - target: who/what is affected by the action.
            - action_type: one of ["attack", "spell", "skill_check", "social", "interact", "movement"]:
                - "attack": physical or weapon-based attack.
                - "spell": casting magic.
                - "skill_check": actions that require a skill to perform - sneaking, perception, disarming.
                - "social": persuading, negotiating, influencing, intimidating, or talking to characters.
                - "interact": manipulating, opening, closing, or using any object, device, container, or entrance 
                (including doors, gates, chests, levers, locks, switches). 
                Always use "interact" for these actions, even if the object could be passed through.
                - "movement": actively traveling from one location to another, including going through entrances.
                Only use "movement" when the action is clearly about changing position or location, 
                not just opening something.
            - weapon: item used for attack or spellcasting.
            - subject: the specific topic, claim, or object of focus — this may be a full phrase or sentence.
            - details: include only clauses that add nuance not covered by other fields. Keep it one sentence max.
            - Output ONLY valid JSON.

            Examples:

            Input: "I try to pick the lock on the chest"
            Output: {
            "actor": "player",
            "action": "pick the lock",
            "target": "chest",
            "action_type": "skill_check",
            "weapon": null,
            "subject": null,
            "details": null
            }

            Input: "I swing my sword at the goblin"
            Output: {
            "actor": "player",
            "action": "swing my sword",
            "target": "goblin",
            "action_type": "attack",
            "weapon": "sword",
            "subject": null,
            "details": null
            }
            """

        return f"""{system_prompt}

        Input: "{user_input}"
        Output: """
    
    def _parse_llama_response(self, response: str, original_input: str) -> ParsedAction:
        """Parse the CodeLlama model's JSON response"""
        # Clean up response
        response = response.strip()
        
        # Remove trailing text
        stop_patterns = [r'\n\nInput:', r'\nInput:', r'\n\n', r'Output:', r'\nExample:']
        for pattern in stop_patterns:
            match = re.search(pattern, response)
            if match:
                response = response[:match.start()]
                break
        
        # Extract JSON
        json_patterns = [
            r'\{[^{}]*"actor"[^{}]*\}',
            r'\{[^{}]*"action"[^{}]*\}',
            r'\{.*?\}',
        ]
        
        json_str = None
        for pattern in json_patterns:
            json_match = re.search(pattern, response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                break
        
        if json_str:
            try:
                # Fix common JSON issues
                json_str = json_str.replace("'", '"')
                json_str = re.sub(r',\s*}', '}', json_str)
                
                parsed_json = json.loads(json_str)
                
                # Validate and convert to ParsedAction
                return ParsedAction(
                    actor=parsed_json.get("actor", "player"),
                    action=parsed_json.get("action", "unknown action"),
                    target=parsed_json.get("target"),
                    action_type=ActionType(self._normalize_action_type(parsed_json.get("action_type", "skill_check"))),
                    weapon=parsed_json.get("weapon"),
                    subject=parsed_json.get("subject"),
                    details=parsed_json.get("details"),
                    parsing_method="codellama"
                )
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[-] JSON parsing failed: {e}")
        
        # Fall back to fallback parser
        print(f"[-] CodeLlama response invalid, using fallback for: '{original_input}'")
        return self.fallback_parser.parse_action(original_input)
    
    def _normalize_action_type(self, action_type: str) -> str:
        """Normalize action type to valid ActionType values"""
        action_type = action_type.lower()
        
        if action_type in [e.value for e in ActionType]:
            return action_type
        
        # Map common variations
        type_mappings = {
            "combat": "attack",
            "magic": "spell", 
            "skill": "skill_check",
            "check": "skill_check",
            "talk": "social",
            "conversation": "social",
            "move": "movement",
            "use": "interact",
            "object": "interact"
        }
        
        return type_mappings.get(action_type, "skill_check")