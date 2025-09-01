"""
Rule-based fallback parser that doesn't require any AI models.
Always available and provides reasonable results for common D&D actions.
"""

import re
from typing import Optional

from backend.game.core.interfaces import ActionParser
from backend.models import ParsedAction, ActionType


class FallbackParser(ActionParser):
    """Rule-based parser using pattern matching and keyword detection"""
    
    def __init__(self):
        self._is_loaded = True  # Always ready
        
        # Define action patterns and mappings
        self.action_patterns = {
            ActionType.ATTACK: {
                "attack": "attack", "strike": "strike", "hit": "strike", 
                "shoot": "ranged attack", "sword": "sword strike", 
                "bow": "bow shot", "dagger": "dagger strike", 
                "axe": "axe swing", "punch": "unarmed strike", 
                "kick": "kick", "slash": "slashing attack", "stab": "stabbing attack",
                "slap": "slapping"
            },
            ActionType.SPELL: {
                "cast": "spell casting", "spell": "spell", 
                "fireball": "fireball spell", "magic missile": "magic missile spell", 
                "heal": "healing spell", "lightning": "lightning spell", 
                "frost": "frost spell", "fire": "fire spell",
                "magic": "magic spell", "enchant": "enchantment spell"
            },
            ActionType.SKILL_CHECK: {
                "sneak": "stealth attempt", "stealth": "stealth attempt", 
                "hide": "hiding attempt", "climb": "climbing", "jump": "jumping", 
                "investigate": "investigation", "search": "searching", 
                "look": "investigation", "examine": "examination",
                "pick": "lock picking", "lockpick": "lock picking", 
                "steal": "theft attempt", "sleight": "sleight of hand", 
                "acrobatics": "acrobatics check", "athletics": "athletics check", 
                "insight": "insight check", "perception": "perception check"
            },
            ActionType.SOCIAL: {
                "talk": "conversation", "speak": "conversation", "say": "conversation",
                "ask": "asking", "tell": "telling", "inquire": "inquiry",
                "bargain": "bargaining", "negotiate": "negotiation", 
                "convince": "persuasion attempt", "persuade": "persuasion attempt", 
                "intimidate": "intimidation", "deceive": "deception", 
                "lie": "deception", "bluff": "deception"
            },
            ActionType.MOVEMENT: {
                "walk": "walking", "run": "running", "move": "movement", 
                "go": "movement", "approach": "approaching", "retreat": "retreating",
                "flee": "fleeing", "dash": "dashing", "step": "stepping"
            },
            ActionType.INTERACT: {
                "open": "opening", "close": "closing", "pull": "pulling",
                "push": "pushing", "use": "using", "touch": "touching",
                "grab": "grabbing", "take": "taking", "pick up": "picking up",
                "activate": "activating", "press": "pressing"
            }
        }
        
        # Common D&D entities for target detection
        self.common_targets = [
            # Creatures
            "goblin", "orc", "dragon", "guard", "skeleton", "zombie", "troll", 
            "bandit", "wolf", "bear", "spider", "rat", "bat", "snake",
            # NPCs
            "merchant", "king", "queen", "priest", "wizard", "knight", "farmer",
            "innkeeper", "blacksmith", "shopkeeper", "barkeep", "barkeeper", "bartender",
            # Objects
            "door", "chest", "lock", "wall", "rope", "lever", "button", 
            "gem", "coin", "sword", "shield", "bow", "potion", "scroll",
            "book", "table", "chair", "window", "stairs", "ladder"
        ]
        
        # Common weapons
        self.weapons = [
            "sword", "blade", "dagger", "knife", "bow", "arrow", "crossbow",
            "axe", "hammer", "mace", "club", "staff", "wand", "spear", "lance",
            "whip", "flail", "scimitar", "rapier", "shortsword", "longsword",
            "greatsword", "katana", "saber", "cutlass", "pistol", "gun",
            "rifle", "musket", "javelin", "halberd", "pike", "trident"
        ]
    
    def load_model(self) -> bool:
        """Fallback parser is always ready"""
        return True
    
    def is_loaded(self) -> bool:
        """Fallback parser is always ready"""
        return True
    
    def parse_action(self, user_input: str, context: str = "") -> ParsedAction:
        """Parse input using rule-based pattern matching"""
        user_input_lower = user_input.lower()
        
        # Default values
        actor = "player"
        action = "basic action"
        target = None
        action_type = ActionType.SKILL_CHECK
        weapon = None
        subject = None
        details = None
        
        # Determine action type and action verb
        for action_type_enum, keywords in self.action_patterns.items():
            for keyword, action_name in keywords.items():
                if keyword in user_input_lower:
                    action_type = action_type_enum
                    action = action_name
                    break
            if action != "basic action":  # Found a match
                break
        
        # Extract components
        target = self._extract_target(user_input, user_input_lower)
        weapon = self._extract_weapon(user_input, user_input_lower)
        subject = self._extract_subject(user_input, user_input_lower)
        
        # Extract details (anything after certain keywords that isn't covered elsewhere)
        details = self._extract_details(user_input, target, weapon, subject)
        
        return ParsedAction(
            actor=actor,
            action=action,
            target=target,
            action_type=action_type,
            weapon=weapon,
            subject=subject,
            details=details,
            parsing_method="fallback"
        )
    
    def _extract_target(self, user_input: str, user_input_lower: str) -> Optional[str]:
        """Extract target using preposition patterns and common entities"""
        
        # Pattern-based extraction
        target_patterns = [
            r'\b(?:at|on|to|with|against|towards?)\s+(?:the\s+)?(\w+)',
            r'\b(?:the)\s+(\w+)(?:\s+(?:with|using))',
            r'\bopen\s+(?:the\s+)?(\w+)',
            r'\bclose\s+(?:the\s+)?(\w+)',
            r'\buse\s+(?:the\s+)?(\w+)',
            r'\btake\s+(?:the\s+)?(\w+)',
            r'\bgrab\s+(?:the\s+)?(\w+)',
            r'\bpick\s+up\s+(?:the\s+)?(\w+)',
            r'\bask\s+(?:the\s+)?(\w+)',
            r'\btell\s+(?:the\s+)?(\w+)',
            r'\btalk\s+to\s+(?:the\s+)?(\w+)'
        ]
        
        for pattern in target_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                target = match.group(1)
                if target not in ["my", "a", "an", "with", "it", "them", "this", "that"]:
                    return target
        
        # Check for common D&D targets
        for target in self.common_targets:
            if target in user_input_lower:
                return target
        
        return None
    
    def _extract_weapon(self, user_input: str, user_input_lower: str) -> Optional[str]:
        """Extract weapon from input"""
        
        # Pattern-based extraction
        weapon_patterns = [
            r'\bwith\s+(?:my\s+|the\s+|a\s+)?(\w+)',
            r'\busing\s+(?:my\s+|the\s+|a\s+)?(\w+)',
            r'\bholding\s+(?:my\s+|the\s+|a\s+)?(\w+)',
            r'\bwielding\s+(?:my\s+|the\s+|a\s+)?(\w+)'
        ]
        
        for pattern in weapon_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                weapon = match.group(1)
                if weapon not in ["hand", "hands", "fist", "fists", "foot", "feet"]:
                    return weapon
        
        # Check for weapon names
        for weapon in self.weapons:
            if weapon in user_input_lower:
                return weapon
        
        return None
    
    def _extract_subject(self, user_input: str, user_input_lower: str) -> Optional[str]:
        """Extract subject/topic from input"""
        
        # Look for "about X" patterns
        about_patterns = [
            r'\babout\s+(?:the\s+)?((?:\w+\s*)+?)(?:\s*$|[.!?]|\s+(?:and|or|but|with|to|at|in|on|for|from))',
            r'\bregarding\s+(?:the\s+)?((?:\w+\s*)+?)(?:\s*$|[.!?])',
            r'\bconcerning\s+(?:the\s+)?((?:\w+\s*)+?)(?:\s*$|[.!?])'
        ]
        
        for pattern in about_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                subject = match.group(1).strip()
                if subject and len(subject) > 0:
                    return subject
        
        # Look for "for X" patterns
        for_patterns = [
            r'\bfor\s+(?:the\s+|any\s+)?((?:\w+\s*)+?)(?:\s*$|[.!?]|\s+(?:and|or|but|with|to|at|in|on|from))',
            r'\blooking\s+for\s+(?:the\s+)?((?:\w+\s*)+?)(?:\s*$|[.!?])',
            r'\bsearching\s+for\s+(?:the\s+)?((?:\w+\s*)+?)(?:\s*$|[.!?])'
        ]
        
        for pattern in for_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                subject = match.group(1).strip()
                if subject and subject not in ["help", "me", "you", "it", "them"]:
                    return subject
        
        return None
    
    def _extract_details(self, user_input: str, target: Optional[str], 
                        weapon: Optional[str], subject: Optional[str]) -> Optional[str]:
        """Extract additional details not covered by other fields"""
        
        # Simple heuristic: look for descriptive phrases after certain keywords
        detail_indicators = [
            "in order to", "so that", "because", "while", "during", "before", "after"
        ]
        
        for indicator in detail_indicators:
            if indicator in user_input.lower():
                # Extract text after the indicator
                parts = user_input.lower().split(indicator, 1)
                if len(parts) > 1:
                    detail = parts[1].strip()
                    # Clean it up and limit length
                    detail = detail.split('.')[0]  # Take first sentence
                    if len(detail) > 100:
                        detail = detail[:100] + "..."
                    return detail if detail else None
        
        return None