import uuid
import json
import logging
from typing import List, Dict, Any, Optional, Set
from prisma import Json
from datetime import datetime, timezone
from backend.game.core.character_state import CharacterState
from backend.models import Scene, TurnPhase

logger = logging.getLogger(__name__)


class GameState:
    """
    Comprehensive game state managing all aspects of the current game session.
    Tracks characters, scene, narrative state, and game progression.
    """

    def __init__(self, game_id: str):
        self.id: Optional[str] = None
        self.game_id = game_id
        self.loaded_scene: Scene = None
        self.turn_counter = 0
        self.current_turn_phase: Optional[str] = None
        self.current_actor: Optional[str] = None
        self.is_player_input_locked = False

        # Game progression - Not sure about these yet
        self.objectives: List[str] = None
        self.completed_objectives: List[str] = None
        self.story_beats: List[str] = None

        # Combat state
        self.in_combat = False
        self.initiative_order: List[str] = None  # Character names in initiative order

        # Environment - Dont know if weather and time will factor in - Time could be based on Turn Count
        self.weather = "clear"
        self.time_of_day = "day"
        self.location_history: List[str] = None

        # Narrative state
        self.recent_events: List[str] = None  # Last few turns of narrative
        self.important_npcs_met: Set[str] = set()
        self.items_discovered: List[str] = None

        # Session metadata
        self.session_started = datetime.now(timezone.utc)
        self.last_updated = datetime.now(timezone.utc)
        self.save_version = "1.0"

    # Character management - TODO: Method of getting npc by name will probably not work later
    def get_npc_by_name(self, name: str) -> Optional[CharacterState]:
        """Find NPC by name"""
        for npc in self.npcs:
            if npc.name.lower() == name.lower():
                return npc
        return None

    def add_npc(self, npc: CharacterState):
        """Add new NPC to the game"""
        self.npcs.append(npc)
        self.last_updated = datetime.now(timezone.utc)

    def remove_npc(self, name: str) -> bool:
        """Remove NPC from game"""
        for i, npc in enumerate(self.npcs):
            if npc.name.lower() == name.lower():
                self.npcs.pop(i)
                self.last_updated = datetime.now(timezone.utc)
                return True
        return False

    def get_all_characters(self) -> List[CharacterState]:
        """Get all characters (player + NPCs)"""
        return [self.player] + self.npcs

    def get_living_characters(self) -> List[CharacterState]:
        """Get all living characters"""
        return [char for char in self.get_all_characters() if char.is_alive()]

    # Combat management - This might need to move to character state
    def start_combat(self, initiative_order: List[str] = None):
        """Start combat encounter"""
        self.in_combat = True
        if initiative_order:
            self.initiative_order = initiative_order
        else:
            # Simple initiative: player first, then NPCs
            self.initiative_order = [self.player.name] + [
                npc.name for npc in self.npcs if npc.is_alive()
            ]

        self.current_turn_character = (
            self.initiative_order[0] if self.initiative_order else None
        )
        self.last_updated = datetime.now(timezone.utc)

    def end_combat(self):
        """End combat encounter"""
        self.in_combat = False
        self.initiative_order = []
        self.current_turn_character = None

        # Reset all character turn states
        for character in self.get_all_characters():
            character.reset_turn_actions()

        self.last_updated = datetime.now(timezone.utc)

    def advance_turn(self):
        """Advance to next character's turn"""
        if not self.in_combat or not self.initiative_order:
            return

        current_index = (
            self.initiative_order.index(self.current_turn_character)
            if self.current_turn_character
            else -1
        )
        next_index = (current_index + 1) % len(self.initiative_order)
        self.current_turn_character = self.initiative_order[next_index]

        # If we've cycled back to the first character, increment turn counter
        if next_index == 0:
            self.turn_counter += 1

            # Update status effects for all characters
            for character in self.get_all_characters():
                character.update_status_effects()

        self.last_updated = datetime.now(timezone.utc)

    # Scene management
    def update_scene(self, new_scene_data: Dict[str, Any]):
        """Update scene information"""
        self.scene.update(new_scene_data)

        # Track location changes
        new_location = new_scene_data.get("name")
        if new_location and (
            not self.location_history or self.location_history[-1] != new_location
        ):
            self.location_history.append(new_location)

        self.last_updated = datetime.now(timezone.utc)

    def add_scene_flag(self, flag: str, value: Any):
        """Add a flag to the current scene"""
        if "flags" not in self.scene:
            self.scene["flags"] = {}
        self.scene["flags"][flag] = value
        self.last_updated = datetime.now(timezone.utc)

    def get_scene_flag(self, flag: str, default: Any = None) -> Any:
        """Get a scene flag value"""
        return self.scene.get("flags", {}).get(flag, default)

    # Objective management
    def add_objective(self, objective: str):
        """Add new objective"""
        if objective not in self.objectives:
            self.objectives.append(objective)
            self.last_updated = datetime.now(timezone.utc)

    def complete_objective(self, objective: str) -> bool:
        """Mark objective as completed"""
        if objective in self.objectives:
            self.objectives.remove(objective)
            self.completed_objectives.append(objective)
            self.last_updated = datetime.now(timezone.utc)
            return True
        return False

    def get_active_objectives(self) -> List[str]:
        """Get list of active objectives"""
        return self.objectives.copy()

    # Story tracking
    def add_story_beat(self, event: str):
        """Add important story event"""
        self.story_beats.append(event)
        self.last_updated = datetime.now(timezone.utc)

    def add_recent_event(self, event: str, max_recent: int = 10):
        """Add to recent events (for narrative context)"""
        self.recent_events.append(event)
        if len(self.recent_events) > max_recent:
            self.recent_events.pop(0)
        self.last_updated = datetime.now(timezone.utc)

    def meet_npc(self, npc_name: str):
        """Record meeting an important NPC"""
        self.important_npcs_met.add(npc_name)
        self.last_updated = datetime.now(timezone.utc)

    # ------------------------------
    # DB CONVERSION
    # ------------------------------

    @classmethod
    def from_db(cls, record):
        obj = cls(record.game_id)
        obj.id = record.id
        obj.turn_counter = record.turn_counter
        obj.current_turn_phase = record.current_turn_phase
        obj.current_actor = record.current_actor
        obj.is_player_input_locked = record.is_player_input_locked
        obj.objectives = record.objectives or []
        obj.completed_objectives = record.completed_objectives or []
        obj.story_beats = record.story_beats or []
        obj.in_combat = record.in_combat
        obj.initiative_order = record.initiative_order or []
        obj.weather = record.weather or "clear"
        obj.time_of_day = record.time_of_day or "day"
        obj.location_history = record.location_history or []
        obj.recent_events = record.recent_events or []
        obj.important_npcs_met = set(record.important_npcs_met or [])
        obj.items_discovered = record.items_discovered or []
        obj.session_started = record.session_started
        obj.save_version = record.save_version
        return obj

    def to_db(self, for_create: bool = False):
        data = {
            "game_id": self.game_id,
            "turn_counter": self.turn_counter,
            "current_turn_phase": self.current_turn_phase,
            "current_actor": self.current_actor,
            "is_player_input_locked": self.is_player_input_locked,
            "objectives": Json(self.objectives or []),
            "completed_objectives": Json(self.completed_objectives or []),
            "story_beats": Json(self.story_beats or []),
            "in_combat": self.in_combat,
            "initiative_order": Json(self.initiative_order or []),
            "weather": self.weather,
            "time_of_day": self.time_of_day,
            "location_history": Json(self.location_history or []),
            "recent_events": Json(self.recent_events or []),
            "important_npcs_met": Json(list(self.important_npcs_met)),
            "items_discovered": Json(self.items_discovered or []),
            "session_started": (
                self.session_started.isoformat() if self.session_started else None
            ),
            "save_version": self.save_version,
        }

        if not for_create:
            data["id"] = self.id
            # optionally include last_updated or other fields for update

        return data

    def to_dict(self):
        return {
            "id": self.id,
            "game_id": self.game_id,
            "turn_counter": self.turn_counter,
            "current_turn_phase": self.current_turn_phase,
            "current_actor": self.current_actor,
            "is_player_input_locked": self.is_player_input_locked,
            "objectives": self.objectives or [],
            "completed_objectives": self.completed_objectives or [],
            "story_beats": self.story_beats or [],
            "in_combat": self.in_combat,
            "initiative_order": self.initiative_order or [],
            "weather": self.weather,
            "time_of_day": self.time_of_day,
            "location_history": self.location_history or [],
            "recent_events": self.recent_events or [],
            "important_npcs_met": list(self.important_npcs_met),
            "items_discovered": self.items_discovered or [],
            "session_started": (
                self.session_started.isoformat() if self.session_started else None
            ),
            "save_version": self.save_version,
        }

    # ------------------------------
    # Serialization
    # ------------------------------

    # def to_dict(self) -> Dict[str, Any]:
    #     """Convert game state to dictionary for saving"""
    #     try:
    #         return {
    #             "id": self.id,
    #             "game_id": self.game_id,
    #             "turn_counter": self.turn_counter,
    #             "in_combat": self.in_combat,
    #             "weather": self.weather,
    #             "time_of_day": self.time_of_day,
    #             "session_started": self.session_started.isoformat(),
    #             "last_updated": self.last_updated.isoformat(),
    #             "save_version": self.save_version,
    #             "loaded_scene": self.loaded_scene or Json({}),
    #             "objectives": self.objectives or Json([]),
    #             "completed_objectives": self.completed_objectives or Json([]),
    #             "story_beats": self.story_beats or Json([]),
    #             "initiative_order": self.initiative_order or Json([]),
    #             "location_history": self.location_history or Json([]),
    #             "recent_events": self.recent_events or Json([]),
    #             "important_npcs_met": self.important_npcs_met or Json([]),
    #             "items_discovered": self.items_discovered or Json([]),
    #         }
    #     except Exception as e:
    #         logging.error(f"Error serializing GameState: {e}")
    #         raise

    # @classmethod
    # def from_dict(cls, data: Dict[str, Any]) -> "GameState":
    #     """Load game state from dictionary with robust error handling"""
    #     try:
    #         game_state = cls()

    #         # Define field mappings with types and defaults
    #         field_mappings = {
    #             "id": (str),
    #             "game_id": (str),
    #             "turn_counter": (int, 0),
    #             "save_version": (str, "1.0"),
    #             "objectives": (list, []),
    #             "completed_objectives": (list, []),
    #             "story_beats": (list, []),
    #             "initiative_order": (list, []),
    #             "location_history": (list, []),
    #             "recent_events": (list, []),
    #             "items_discovered": (list, []),
    #             "weather": (str, "clear"),
    #             "time_of_day": (str, "day"),
    #             "current_turn_character": (type(None), None),  # Optional string
    #             "in_combat": (bool, False),
    #             "loaded_scene": (dict, {}),
    #         }

    #         # Apply field mappings with type checking
    #         for field_name, (expected_type, default_value) in field_mappings.items():
    #             try:
    #                 value = data.get(field_name, default_value)

    #                 # Handle optional fields (like current_turn_character)
    #                 if expected_type == type(None) and value is None:
    #                     setattr(game_state, field_name, value)
    #                 elif value is not None and not isinstance(value, expected_type):
    #                     # Try to convert the type
    #                     if expected_type == list and not isinstance(value, list):
    #                         value = [value] if value else []
    #                     elif expected_type == dict and not isinstance(value, dict):
    #                         value = default_value
    #                     elif expected_type in (str, int, bool):
    #                         value = expected_type(value)

    #                 setattr(game_state, field_name, value)

    #             except (ValueError, TypeError) as e:
    #                 logging.warning(
    #                     f"Error setting field {field_name}: {e}. Using default value."
    #                 )
    #                 setattr(game_state, field_name, default_value)

    #         # Handle datetime fields with fallbacks
    #         datetime_fields = {
    #             "session_started": datetime.now(timezone.utc),
    #             "last_updated": datetime.now(timezone.utc),
    #         }

    #         for field_name, fallback in datetime_fields.items():
    #             try:
    #                 value = data.get(field_name)
    #                 if value:
    #                     if isinstance(value, str):
    #                         setattr(
    #                             game_state, field_name, datetime.fromisoformat(value)
    #                         )
    #                     elif isinstance(value, datetime):
    #                         setattr(game_state, field_name, value)
    #                     else:
    #                         setattr(game_state, field_name, fallback)
    #                 else:
    #                     setattr(game_state, field_name, fallback)
    #             except (ValueError, TypeError) as e:
    #                 logging.warning(
    #                     f"Error parsing datetime field {field_name}: {e}. Using current time."
    #                 )
    #                 setattr(game_state, field_name, fallback)

    #         # Handle sets (important_npcs_met)
    #         try:
    #             npcs_met_data = data.get("important_npcs_met", [])
    #             if isinstance(npcs_met_data, (list, set)):
    #                 game_state.important_npcs_met = set(
    #                     str(item) for item in npcs_met_data
    #                 )
    #             else:
    #                 game_state.important_npcs_met = set()
    #         except Exception as e:
    #             logging.warning(f"Error processing important_npcs_met: {e}")
    #             game_state.important_npcs_met = set()

    #         # Update last_updated to reflect loading
    #         game_state.last_updated = datetime.now(timezone.utc)

    #         return game_state

    #     except Exception as e:
    #         logging.error(f"Critical error deserializing GameState: {e}")
    #         raise

    def validate_state(self) -> bool:
        """Validate the game state integrity"""
        try:
            # Check required fields exist
            required_attrs = ["game_id", "player", "npcs", "turn_counter"]
            for attr in required_attrs:
                if not hasattr(self, attr):
                    logging.error(f"Missing required attribute: {attr}")
                    return False

            # Check types
            if not isinstance(self.npcs, list):
                logging.error("NPCs is not a list")
                return False

            if not isinstance(self.turn_counter, int) or self.turn_counter < 0:
                logging.error("Invalid turn counter")
                return False

            if not isinstance(self.important_npcs_met, set):
                logging.error("important_npcs_met is not a set")
                return False

            return True

        except Exception as e:
            logging.error(f"Error during state validation: {e}")
            return False

    def upgrade_save_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle upgrading old save data formats"""
        current_version = data.get("save_version", "0.0")

        # Example migration from version 0.0 to 1.0
        if current_version == "0.0":
            # Add any new fields that didn't exist in 0.0
            if "weather" not in data:
                data["weather"] = "clear"
            if "time_of_day" not in data:
                data["time_of_day"] = "day"
            data["save_version"] = "1.0"

        # Future migrations can be added here
        # elif current_version == "1.0":
        #     # Migrate from 1.0 to 1.1
        #     pass

        return data

    # Example usage and testing functions
    def test_serialization():
        """Test the serialization/deserialization process"""
        # This would require your CharacterState class to be implemented
        # For testing purposes, you might create a mock CharacterState

        class MockCharacterState:
            def __init__(self, name="Test Player"):
                self.name = name

            def to_dict(self):
                return {"name": self.name}

            @classmethod
            def from_dict(cls, data):
                return cls(data.get("name", "Unknown"))

        # Create test game state
        player = MockCharacterState("Hero")
        game_state = GameState(player)

        # Serialize
        data = game_state.to_dict()
        print("Serialization successful")

        # Deserialize
        loaded_state = GameState.from_dict(data)
        print("Deserialization successful")

        # Validate
        is_valid = loaded_state.validate_state()
        print(f"State validation: {'Passed' if is_valid else 'Failed'}")

        return loaded_state


# Uncomment to test
# test_serialization()

# def save_to_file(self, filepath: str):
#     """Save game state to JSON file"""
#     with open(filepath, "w") as f:
#         json.dump(self.to_dict(), f, indent=2)

# @classmethod
# def load_from_file(cls, filepath: str) -> "GameState":
#     """Load game state from JSON file"""
#     with open(filepath, "r") as f:
#         data = json.load(f)
#     return cls.from_dict(data)
