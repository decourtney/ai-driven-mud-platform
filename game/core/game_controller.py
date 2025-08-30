import asyncio
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor
import threading
from game.core.models import GameCondition
from game.core.game_engine import GameEngine, StandardDiceRoller
from game.core.model_manager import ModelManager

class StreamingGameController:
    """
    Controller for managing the streaming game loop with immediate feedback.
    Separates UI updates from game processing for better responsiveness.
    """
    
    def __init__(self, game_engine: GameEngine, display_callback: Callable[[str], None]):
        self.engine = game_engine
        self.display = display_callback  # Function to display text to user
        self.executor = ThreadPoolExecutor(max_workers=2)  # For background processing
        
    def run_streaming_turn(self, user_input: str):
        """
        Execute a turn with streaming narration delivery.
        This is the main method your UI would call.
        """
        # 1. Show current scene first
        scene_description = self.engine.get_current_scene()
        self.display(f"Scene: {scene_description}\n")
        
        # 2. Process player input immediately
        player_narration, condition, should_continue = self.engine.process_player_input_immediate(user_input)
        self.display(f"Player: {player_narration}\n")
        
        # 3. Check if game ends after player action
        if condition != GameCondition.CONTINUE:
            self.display(f"Game Over: {condition.value}")
            return condition
        
        if not should_continue:
            # Player needs to re-enter input (validation failed)
            return GameCondition.CONTINUE
            
        # 4. Process NPCs with streaming updates
        return self._process_npc_turn_streaming()
    
    def _process_npc_turn_streaming(self) -> GameCondition:
        """Process NPC actions with immediate narration display"""
        living_npcs = self.engine.get_living_npcs()
        
        if not living_npcs:
            # No NPCs to process, go straight to scene update
            return self._update_scene_and_finish()
        
        self.display("--- NPC Turn ---")
        
        # Process each NPC immediately
        for i, npc in enumerate(living_npcs):
            # Show waiting message
            self.display(f"⏳ {npc.name} is deciding...")
            
            # Process this NPC's action
            npc_narration, success = self.engine.process_single_npc_action(npc)
            
            if npc_narration:
                self.display(f"{npc.name}: {npc_narration}")
            
            # Check condition after each NPC (in case player dies)
            current_condition = self.engine.check_game_condition()
            if current_condition != GameCondition.CONTINUE:
                self.display(f"Game Over: {current_condition.value}")
                return current_condition
        
        # All NPCs processed, now update scene
        return self._update_scene_and_finish()
    
    def _update_scene_and_finish(self) -> GameCondition:
        """Update scene description and finish turn"""
        self.display("⏳ Updating world state...")
        
        # This can run in background while we display the message
        scene_description, final_condition = self.engine.get_updated_scene_after_actions()
        
        self.display("--- Turn Complete ---")
        return final_condition


# Async version for even better responsiveness
class AsyncStreamingGameController:
    """
    Async version that can handle background processing even better.
    Use this if your UI framework supports async (like modern web frameworks).
    """
    
    def __init__(self, game_engine: GameEngine, display_callback: Callable[[str], None]):
        self.engine = game_engine
        self.display = display_callback
        
    async def run_streaming_turn_async(self, user_input: str):
        """Async version of streaming turn execution"""
        # 1. Show current scene
        scene_description = self.engine.get_current_scene()
        self.display(f"Scene: {scene_description}\n")
        
        # 2. Process player input
        player_narration, condition, should_continue = self.engine.process_player_input_immediate(user_input)
        self.display(f"Player: {player_narration}\n")
        
        if condition != GameCondition.CONTINUE or not should_continue:
            return condition
            
        # 3. Process NPCs with async updates
        return await self._process_npc_turn_async()
    
    async def _process_npc_turn_async(self) -> GameCondition:
        """Async NPC processing with concurrent scene updates"""
        living_npcs = self.engine.get_living_npcs()
        
        if not living_npcs:
            return await self._update_scene_async()
        
        self.display("--- NPC Turn ---")
        
        # Start scene update in background while processing NPCs
        scene_update_task = asyncio.create_task(self._update_scene_async())
        
        # Process NPCs
        for npc in living_npcs:
            self.display(f"⏳ {npc.name} is deciding...")
            
            # Run NPC processing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            npc_narration, success = await loop.run_in_executor(
                None, self.engine.process_single_npc_action, npc
            )
            
            if npc_narration:
                self.display(f"{npc.name}: {npc_narration}")
            
            # Quick condition check
            current_condition = self.engine.check_game_condition()
            if current_condition != GameCondition.CONTINUE:
                scene_update_task.cancel()
                return current_condition
        
        # Wait for scene update to complete
        await scene_update_task
        self.display("--- Turn Complete ---")
        return GameCondition.CONTINUE
    
    async def _update_scene_async(self) -> GameCondition:
        """Update scene in background"""
        loop = asyncio.get_event_loop()
        scene_description, condition = await loop.run_in_executor(
            None, self.engine.get_updated_scene_after_actions
        )
        return condition



# Simple example of how to use the streaming controller
def example_usage():
    """Example of how to integrate the streaming game loop"""
    engine = GameEngine(
      model_manager=ModelManager(),
      dice_roller=StandardDiceRoller()
    )
    
    # Your display function (could be print, web socket send, GUI update, etc.)
    def display_to_user(text: str):
        print(text)  # Replace with your actual display method
    
    # Initialize
    controller = StreamingGameController(engine, display_to_user)
    
    # Main game loop
    while True:
        # Get user input
        user_input = input("\nWhat do you do? ")
        
        if user_input.lower() in ['quit', 'exit']:
            break
            
        # Process turn with streaming updates
        final_condition = controller.run_streaming_turn(user_input)
        
        # Check if game ended
        if final_condition != GameCondition.CONTINUE:
            print(f"\n🎮 Game ended: {final_condition.value}")
            break
        
        print("\n" + "="*50)  # Turn separator


# For web applications or other async frameworks
async def async_example_usage():
    """Example for async/web applications"""
    engine = GameEngine(
      model_manager=ModelManager(),
      dice_roller=StandardDiceRoller()
    )
        
    async def display_to_websocket(text: str):
        # Replace with your actual websocket/async display method
        print(f"[WebSocket] {text}")
    
    controller = AsyncStreamingGameController(engine, display_to_websocket)
    
    # This would be called when receiving user input via websocket/API
    user_input = "attack the goblin"
    final_condition = await controller.run_streaming_turn_async(user_input)
    
    return final_condition


# Timeline example of what the user experiences:
"""
USER EXPERIENCE TIMELINE:

1. User enters: "attack the goblin"
2. IMMEDIATE display: "Player: You swing your sword at the goblin! [dice roll: 15] You hit for 8 damage!"
3. IMMEDIATE display: "⏳ Waiting for NPC turn"
4. ~1-2 seconds later: "⏳ Goblin is deciding..."
5. IMMEDIATE display: "Goblin: The goblin snarls and attacks you! [dice roll: 12] The goblin misses!"
6. IMMEDIATE display: "⏳ Updating world state..."
7. ~1-2 seconds later: "--- Turn Complete ---"
8. Ready for next input

Total wait time: ~2-4 seconds spread across the turn instead of 5-10 seconds at the end
User sees progress throughout instead of staring at a spinner
"""