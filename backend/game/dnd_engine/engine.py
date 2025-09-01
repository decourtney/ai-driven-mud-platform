from backend.game.core.base_engine import BaseGameEngine

class DndEngine(BaseGameEngine):
    def initialize_game_state(self, **kwargs):
        # Call base if needed
        super().initialize_game_state(**kwargs)
        self.state = {
            "scene": "spaceport",
            "player": {"hp": 100, "inventory": []},
            "npcs": [{"name": "Captain Vega", "mood": "neutral"}]
        }

    def validate_action(self, action):
        # Example: space quest–specific rules
        if action not in ["talk", "explore", "launch"]:
            return False
        return True
