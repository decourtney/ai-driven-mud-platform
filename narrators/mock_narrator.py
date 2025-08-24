"""
Mock narrator for testing and development.
Provides simple rule-based narration without requiring AI models.
"""

from typing import Optional
from core.interfaces import ActionNarrator
from core.models import ParsedAction, ActionType


class MockNarrator(ActionNarrator):
    """Simple rule-based narrator for testing"""
    
    def __init__(self):
        self._is_loaded = False
        
        # Template-based narrations
        self.templates = {
            ActionType.ATTACK: {
                "hit": {
                    "wound": "{actor} strikes {target} with {weapon}, dealing damage.",
                    "critical": "{actor} lands a devastating blow against {target}!",
                    "kill": "{actor} delivers a fatal strike to {target}."
                },
                "failure": {
                    "miss": "{actor} swings at {target} but misses."
                }
            },
            ActionType.SPELL: {
                "hit": {
                    "wound": "{actor} casts {action} at {target}, the magic takes effect.",
                    "critical": "{actor}'s {action} strikes {target} with incredible power!",
                    "kill": "{actor}'s {action} completely overwhelms {target}."
                },
                "failure": {
                    "miss": "{actor} attempts to cast {action} but the spell fails."
                }
            },
            ActionType.SKILL_CHECK: {
                "hit": {
                    "success": "{actor} successfully completes {action}.",
                    "great_success": "{actor} performs {action} with exceptional skill!",
                    "outstanding_success": "{actor} achieves remarkable success with {action}!"
                },
                "failure": {
                    "failure": "{actor} fails to complete {action}."
                }
            },
            ActionType.SOCIAL: {
                "hit": {
                    "success": "{actor} successfully engages in {action} with {target}.",
                    "great_success": "{actor}'s {action} is very effective with {target}.",
                    "outstanding_success": "{actor} completely wins over {target} with {action}!"
                },
                "failure": {
                    "failure": "{actor}'s attempt at {action} with {target} falls flat."
                }
            },
            ActionType.MOVEMENT: {
                "hit": {
                    "success": "{actor} successfully performs {action}.",
                    "great_success": "{actor} moves with grace and speed.",
                    "outstanding_success": "{actor} moves with incredible agility!"
                },
                "failure": {
                    "failure": "{actor} stumbles while attempting {action}."
                }
            },
            ActionType.INTERACT: {
                "hit": {
                    "success": "{actor} successfully interacts with {target}.",
                    "great_success": "{actor} deftly manipulates {target}.",
                    "outstanding_success": "{actor} expertly handles {target}!"
                },
                "failure": {
                    "failure": "{actor} fails to properly interact with {target}."
                }
            }
        }
    
    def load_model(self) -> bool:
        """Mock narrator is always ready"""
        self._is_loaded = True
        return True
    
    def is_loaded(self) -> bool:
        """Check if narrator is ready"""
        return self._is_loaded
    
    def generate_narration(self, action: ParsedAction, dice_roll: int, 
                          hit: bool, damage_type: str = "wound") -> str:
        """Generate simple template-based narration"""
        if not self.is_loaded():
            return "The narrator is not ready."
        
        # Get appropriate template
        action_templates = self.templates.get(action.action_type)
        if not action_templates:
            return f"{action.actor} performs {action.action}."
        
        outcome = "hit" if hit else "failure"
        outcome_templates = action_templates.get(outcome, {})
        
        template = outcome_templates.get(damage_type)
        if not template:
            # Fallback to generic template
            if hit:
                template = "{actor} successfully performs {action}."
            else:
                template = "{actor} fails to perform {action}."
        
        # Fill in template variables
        narration = template.format(
            actor=action.actor,
            action=action.action,
            target=action.target or "the target",
            weapon=action.weapon or "their weapon",
            subject=action.subject or "",
            roll=dice_roll
        )
        
        # Add subject context if present
        if action.subject and "{subject}" not in template:
            narration += f" (regarding {action.subject})"
        
        # Add details if present
        if action.details:
            narration += f" {action.details}"
        
        return narration