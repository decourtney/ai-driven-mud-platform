"""
Pygmalion-based narrator implementing the ActionNarrator interface.
Uses Pygmalion 2-7B with LoRA adapter for D&D action narration.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM , BitsAndBytesConfig
from peft import PeftModel
from mistral_inference.transformer import Transformer
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
import re
import os
from typing import Optional
import gc

from core.interfaces import ActionNarrator
from core.models import ParsedAction, ActionType


class PygmalionNarrator(ActionNarrator):
    """Pygmalion-based D&D action narrator"""
    
    def __init__(
        self, 
        model_name: str = "/home/donovan/ai_models/pygmalion-2-7b",
        adapter_path: Optional[str] = "/home/donovan/ai_projects/pygmalion-lora/lora_output",
        offload_dir: Optional[str] = "/home/donovan/ai_projects/pygmalion-lora/offload"
    ):
        self.model_name = model_name
        self.adapter_path = adapter_path
        self.offload_dir = offload_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )
        
        self.tokenizer = None
        self.base_model = None
        self.model = None
        self._is_loaded = False
        
        
    def load_model(self) -> bool:
        """Load the Pygmalion model and LoRA adapter"""
        try:
            print(f"[+] Loading Pygmalion narrator from {self.model_name}...")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load base model
            self.base_model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="auto",
                offload_folder=self.offload_dir if self.offload_dir else None,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                quantization_config=self.bnb_config
            )
            
            # Load LoRA adapter if provided
            # if self.adapter_path and os.path.exists(self.adapter_path):
            #     print(f"[+] Loading LoRA adapter from {self.adapter_path}...")
            #     self.model = PeftModel.from_pretrained(
            #         self.base_model,
            #         self.adapter_path,
            #         device_map="auto",
            #         offload_folder=self.offload_dir if self.offload_dir else None
            #     )
            #     self.model.eval()
            #     print("[+] LoRA adapter loaded")
            # else:
            #     print("[+] No LoRA adapter found, using base model")
            #     self.model = self.base_model
            
            # FIXED: Always assign base_model to model when not using adapter
            print("[+] Using base model without LoRA adapter")
            self.model = self.base_model
            
            self._is_loaded = True
            print(f"[+] Pygmalion narrator loaded on {self.device}")
            return True
            
        except Exception as e:
            print(f"[-] Failed to load Pygmalion narrator: {e}")
            self._is_loaded = False
            return False
        
    def unload_model(self) -> bool:
        """Unload the model to free GPU/CPU resources"""
        try:
            if self.model is not None:
                del self.model
            if self.base_model is not None:
                del self.base_model
            if self.tokenizer is not None:
                del self.tokenizer
                
            self.model = None
            self.base_model = None
            self.tokenizer = None
            
            gc.collect()
                
            # Clear GPU cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.ipc_collect()
                torch.cuda.synchronize()                 
            
            self._is_loaded = False
            
            print("[+] Narrator unloaded successfully")
            return True
        except Exception as e:
            print(f"[-] Error unloading Pygmalion: {e}")
            return False
    
    def is_loaded(self) -> bool:
        """Check if narrator is ready to use"""
        return self._is_loaded and self.model is not None
    
    def generate_input_narration(self, action: ParsedAction, 
                          hit: bool, damage_type: str = "wound") -> str:
        """Generate narrative description of an action"""
        if not self.is_loaded():
            return f"{action.actor} performs {action.action}."
        
        try:
            prompt = self._create_prompt(action, hit, damage_type)
            raw_text = self._generate_text(prompt)
            cleaned_text = self._clean_narration(raw_text, action.actor, action.target)
            return cleaned_text
            
        except Exception as e:
            print(f"[-] Narration generation failed: {e}")
            return f"{action.actor} performs {action.action}."
    
    def _create_prompt(self, action: ParsedAction,
                      hit: bool, damage_type: str) -> str:
        """Create Pygmalion-formatted prompt based on action and outcome"""
        
        # More specific persona that emphasizes following the scenario
        NARRATOR_PERSONA = (
            "Narrator's Persona: Narrator is a skilled D&D dungeon master who describes exactly "
            "what happens in combat with vivid, cinematic detail. Narrator always describes the "
            "specific action that just occurred, using sensory descriptions and dynamic verbs. "
            "Narrator maintains third-person perspective and focuses only on the immediate action "
            "without adding unrelated events. Narrator avoids game mechanics in descriptions."
        )
        
        actor = action.actor
        target = action.target or "the target"
        action_desc = action.action
        
        # Add weapon to action description if present
        if action.weapon and action.action_type == ActionType.ATTACK:
            if action.weapon not in action_desc:
                action_desc = f"{action_desc} with {action.weapon}"
        
        # Build the scenario context based on action outcome
        if not hit:
            # Failed attempts
            if action.action_type == ActionType.SKILL_CHECK:
                scenario = f"{actor} attempts to {action_desc} but fails to succeed."
            elif action.action_type == ActionType.SPELL:
                scenario = f"{actor} tries to cast {action_desc} against {target} but the magic fails."
            elif action.action_type == ActionType.SOCIAL:
                scenario = f"{actor} attempts to {action_desc} with {target} but fails to persuade them."
            else:  # attack, movement, interact
                scenario = f"{actor} tries to {action_desc} against {target} but misses completely."
        else:
            # Successful actions
            if action.action_type == ActionType.SKILL_CHECK:
                if damage_type == "outstanding_success":
                    scenario = f"{actor} executes {action_desc} with masterful skill."
                elif damage_type == "great_success":
                    scenario = f"{actor} performs {action_desc} with expert technique."
                else:
                    scenario = f"{actor} successfully completes {action_desc}."
            elif action.action_type == ActionType.SPELL:
                if damage_type == "kill":
                    scenario = f"{actor} unleashes devastating {action_desc} magic that proves fatal to {target}."
                elif damage_type == "critical":
                    scenario = f"{actor} casts powerful {action_desc} that severely affects {target}."
                else:
                    scenario = f"{actor} successfully casts {action_desc} against {target}."
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
                    scenario = f"{actor} successfully strikes {target} with {action_desc}."
            else:  # movement, interact
                scenario = f"{actor} successfully performs {action_desc}."
        
        # Construct the Pygmalion prompt with clearer context
        prompt = f"""{NARRATOR_PERSONA}
            <START>
            You: {scenario}
            Narrator:"""
                    
        return prompt
    
    def _generate_text(self, prompt: str, max_new_tokens: int = 64, temperature: float = 0.4) -> str:
        """Generate text using the loaded model"""
        inputs = self.tokenizer(
            prompt, 
            return_tensors="pt", 
            padding=True, 
            truncation=True, 
            max_length=512
        )
        
        # Move ALL inputs to the same device as model
        if self.device == "cuda":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            output = self.model.generate(
                **inputs, 
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.8,
                top_k=40,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Only decode the new tokens
        new_tokens = output[0][inputs['input_ids'].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True)
    
    def _clean_narration(self, text: str, actor_name: Optional[str] = None, 
                     target_name: Optional[str] = None) -> str:
        """Clean up the generated narration text with Pygmalion-specific guardrails"""

        # Strip whitespace
        text = text.strip()

        # Remove Pygmalion artifacts
        artifacts = [
            "YOUR TURN", "NEXT TURN", "*rolls dice*", "*", "{{", "}}", "[", "]", 
            "OOC:", "Turn:", "Round:", "What do you do?", "Your move", "It's your turn", 
            "Roll for", "Make a", "You:", "Game Master:", "Narrator:", "<START>", "Persona:",
            '"', "'"
        ]
        for artifact in artifacts:
            text = re.sub(re.escape(artifact), "", text, flags=re.IGNORECASE)

        # Remove character prefixes
        text = re.sub(r'^[^:]*:', '', text).strip()

        # Remove surrounding quotes
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()

        # Take only first sentence
        sentences = re.split(r'[.!?]+', text)
        if sentences:
            text = sentences[0].strip()
        if not text:
            text = "The action occurs."

        # Replace generic terms with actor/target names
        if actor_name and target_name:
            generic_terms = {
                r'\b(the )?character\b': actor_name,
                r'\b(the )?player\b': actor_name,
                r'\b(the )?hero\b': actor_name,
                r'\b(the )?protagonist\b': actor_name,
                r'\b(the )?attacker\b': actor_name,
                r'\b(the )?caster\b': actor_name,
                r'\b(the )?target\b': target_name,
                r'\b(the )?enemy\b': target_name,
                r'\b(the )?opponent\b': target_name,
                r'\b(the )?foe\b': target_name,
                r'\b(the )?victim\b': target_name
            }
            for pattern, replacement in generic_terms.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

            # Replace pronouns referring to actor if not already present
            if actor_name.lower() not in text.lower():
                text = re.sub(r'\bhe\b', actor_name, text, count=1, flags=re.IGNORECASE)
                text = re.sub(r'\bhis\b', f"{actor_name}'s", text, count=1, flags=re.IGNORECASE)

        # Normalize whitespace and strip punctuation
        text = re.sub(r'\s+', ' ', text).strip(' .,!?')

        # Reject off-topic/conversational outputs
        rejection_patterns = [
            r'how can i help', r'what would you like', r'thank you', r'you\'re welcome',
            r'let me know', r'i hope', r'is there anything', r'would you like me to',
            r'i\'d be happy to', r'please let me know'
        ]
        for pattern in rejection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return "The action takes place as intended."

        # Length and content checks
        if len(text.strip()) < 5 or len(text) > 200 or re.match(r'^[^a-zA-Z]*$', text):
            return "The action occurs as described."

        # Ensure capitalization and punctuation
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        if text and text[-1] not in '.!?':
            text += '.'

        return text
