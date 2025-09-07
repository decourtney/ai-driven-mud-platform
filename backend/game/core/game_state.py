from typing import List, Dict, Any, Optional, Set
import uuid
import json
from datetime import datetime
from backend.game.core.character_state import CharacterState

class GameState:
    """
    Comprehensive game state managing all aspects of the current game session.
    Tracks characters, scene, narrative state, and game progression.
    """
    
    def __init__(
        self,
        player: CharacterState,
        npcs: List[CharacterState],
        scene: Dict[str, Any],
        turn_counter: int = 0,
    ):
        self.game_id = str(uuid.uuid4())
        self.player = player
        self.npcs = npcs
        self.scene = scene
        self.turn_counter = turn_counter
        
        # Game progression
        self.objectives: List[str] = []
        self.completed_objectives: List[str] = []
        self.story_beats: List[str] = []  # Major story moments
        
        # Combat state
        self.in_combat = False
        self.initiative_order: List[str] = []  # Character names in initiative order
        self.current_turn_character: Optional[str] = None
        
        # Environment
        self.weather = "clear"
        self.time_of_day = "day"
        self.location_history: List[str] = []
        
        # Narrative state
        self.recent_events: List[str] = []  # Last few turns of narrative
        self.important_npcs_met: Set[str] = set()
        self.items_discovered: List[str] = []
        
        # Session metadata
        self.session_started = datetime.now()
        self.last_updated = datetime.now()
        self.save_version = "1.0"
    
    # Character management - might have to change this to use IDs instead of names
    def get_npc_by_name(self, name: str) -> Optional[CharacterState]:
        """Find NPC by name"""
        for npc in self.npcs:
            if npc.name.lower() == name.lower():
                return npc
        return None
    
    def add_npc(self, npc: CharacterState):
        """Add new NPC to the game"""
        self.npcs.append(npc)
        self.last_updated = datetime.now()
    
    def remove_npc(self, name: str) -> bool:
        """Remove NPC from game"""
        for i, npc in enumerate(self.npcs):
            if npc.name.lower() == name.lower():
                self.npcs.pop(i)
                self.last_updated = datetime.now()
                return True
        return False
    
    def get_all_characters(self) -> List[CharacterState]:
        """Get all characters (player + NPCs)"""
        return [self.player] + self.npcs
    
    def get_living_characters(self) -> List[CharacterState]:
        """Get all living characters"""
        return [char for char in self.get_all_characters() if char.is_alive()]
    
    # Combat management
    def start_combat(self, initiative_order: List[str] = None):
        """Start combat encounter"""
        self.in_combat = True
        if initiative_order:
            self.initiative_order = initiative_order
        else:
            # Simple initiative: player first, then NPCs
            self.initiative_order = [self.player.name] + [npc.name for npc in self.npcs if npc.is_alive()]
        
        self.current_turn_character = self.initiative_order[0] if self.initiative_order else None
        self.last_updated = datetime.now()
    
    def end_combat(self):
        """End combat encounter"""
        self.in_combat = False
        self.initiative_order = []
        self.current_turn_character = None
        
        # Reset all character turn states
        for character in self.get_all_characters():
            character.reset_turn_actions()
        
        self.last_updated = datetime.now()
    
    def advance_turn(self):
        """Advance to next character's turn"""
        if not self.in_combat or not self.initiative_order:
            return
        
        current_index = self.initiative_order.index(self.current_turn_character) if self.current_turn_character else -1
        next_index = (current_index + 1) % len(self.initiative_order)
        self.current_turn_character = self.initiative_order[next_index]
        
        # If we've cycled back to the first character, increment turn counter
        if next_index == 0:
            self.turn_counter += 1
            
            # Update status effects for all characters
            for character in self.get_all_characters():
                character.update_status_effects()
        
        self.last_updated = datetime.now()
    
    # Scene management
    def update_scene(self, new_scene_data: Dict[str, Any]):
        """Update scene information"""
        self.scene.update(new_scene_data)
        
        # Track location changes
        new_location = new_scene_data.get("name")
        if new_location and (not self.location_history or self.location_history[-1] != new_location):
            self.location_history.append(new_location)
        
        self.last_updated = datetime.now()
    
    def add_scene_flag(self, flag: str, value: Any):
        """Add a flag to the current scene"""
        if "flags" not in self.scene:
            self.scene["flags"] = {}
        self.scene["flags"][flag] = value
        self.last_updated = datetime.now()
    
    def get_scene_flag(self, flag: str, default: Any = None) -> Any:
        """Get a scene flag value"""
        return self.scene.get("flags", {}).get(flag, default)
    
    # Objective management
    def add_objective(self, objective: str):
        """Add new objective"""
        if objective not in self.objectives:
            self.objectives.append(objective)
            self.last_updated = datetime.now()
    
    def complete_objective(self, objective: str) -> bool:
        """Mark objective as completed"""
        if objective in self.objectives:
            self.objectives.remove(objective)
            self.completed_objectives.append(objective)
            self.last_updated = datetime.now()
            return True
        return False
    
    def get_active_objectives(self) -> List[str]:
        """Get list of active objectives"""
        return self.objectives.copy()
    
    # Story tracking
    def add_story_beat(self, event: str):
        """Add important story event"""
        self.story_beats.append(event)
        self.last_updated = datetime.now()
    
    def add_recent_event(self, event: str, max_recent: int = 10):
        """Add to recent events (for narrative context)"""
        self.recent_events.append(event)
        if len(self.recent_events) > max_recent:
            self.recent_events.pop(0)
        self.last_updated = datetime.now()
    
    def meet_npc(self, npc_name: str):
        """Record meeting an important NPC"""
        self.important_npcs_met.add(npc_name)
        self.last_updated = datetime.now()
    
    # Serialization
    def to_dict(self) -> Dict[str, Any]:
        """Convert game state to dictionary for saving"""
        return {
            "game_id": self.game_id,
            "player": self.player.to_dict(),
            "npcs": [npc.to_dict() for npc in self.npcs],
            "scene": self.scene,
            "turn_counter": self.turn_counter,
            
            # Game progression
            "objectives": self.objectives,
            "completed_objectives": self.completed_objectives,
            "story_beats": self.story_beats,
            
            # Combat state
            "in_combat": self.in_combat,
            "initiative_order": self.initiative_order,
            "current_turn_character": self.current_turn_character,
            
            # Environment
            "weather": self.weather,
            "time_of_day": self.time_of_day,
            "location_history": self.location_history,
            
            # Narrative
            "recent_events": self.recent_events,
            "important_npcs_met": list(self.important_npcs_met),
            "items_discovered": self.items_discovered,
            
            # Metadata
            "session_started": self.session_started.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "save_version": self.save_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameState':
        """Load game state from dictionary"""
        # Restore player
        player = CharacterState.from_dict(data["player"])
        
        # Restore NPCs
        npcs = [CharacterState.from_dict(npc_data) for npc_data in data["npcs"]]
        
        # Create game state
        game_state = cls(
            player=player,
            npcs=npcs,
            scene=data["scene"],
            turn_counter=data["turn_counter"],
        )
        
        # Restore other attributes
        for key, value in data.items():
            if hasattr(game_state, key) and key not in ["player", "npcs", "scene", "turn_counter", "global_flags", "important_npcs_met"]:
                if key in ["session_started", "last_updated"]:
                    value = datetime.fromisoformat(value)
                setattr(game_state, key, value)
        
        # Restore sets
        game_state.important_npcs_met = set(data.get("important_npcs_met", []))
        
        return game_state
    
    def save_to_file(self, filepath: str):
        """Save game state to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'GameState':
        """Load game state from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)