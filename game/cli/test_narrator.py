#!/usr/bin/env python3
"""
Standalone narrator testing tool.
Allows testing different narrators in isolation without loading other components.
"""

import sys
import argparse
from typing import List

# Add parent directory to path for imports
sys.path.append('..')

from game.narrators.mock_narrator import MockNarrator
from game.core.models import ParsedAction, ActionType


class NarratorTester:
    """Interactive narrator testing utility"""
    
    def __init__(self):
        self.narrators = {
            'pygmalion': None,
            'mock': MockNarrator()
        }
        
        # Load mock narrator (always available)
        self.narrators['mock'].load_model()
        
        # Test cases for batch testing
        self.test_cases = [
            {
                'action': ParsedAction(
                    actor="Thorin",
                    action="sword strike", 
                    target="goblin",
                    action_type=ActionType.ATTACK,
                    weapon="sword"
                ),
                'scenarios': [
                    {'roll': 5, 'success': False, 'damage_type': 'miss'},
                    {'roll': 12, 'success': True, 'damage_type': 'wound'},
                    {'roll': 18, 'success': True, 'damage_type': 'wound'},
                    {'roll': 20, 'success': True, 'damage_type': 'critical'}
                ]
            },
            {
                'action': ParsedAction(
                    actor="Gandalf",
                    action="fireball",
                    target="orc",
                    action_type=ActionType.SPELL
                ),
                'scenarios': [
                    {'roll': 8, 'success': False, 'damage_type': 'miss'},
                    {'roll': 15, 'success': True, 'damage_type': 'wound'},
                    {'roll': 19, 'success': True, 'damage_type': 'critical'},
                    {'roll': 20, 'success': True, 'damage_type': 'kill'}
                ]
            },
            {
                'action': ParsedAction(
                    actor="Legolas",
                    action="stealth past the guards",
                    target="guards",
                    action_type=ActionType.SKILL_CHECK
                ),
                'scenarios': [
                    {'roll': 7, 'success': False, 'damage_type': 'failure'},
                    {'roll': 13, 'success': True, 'damage_type': 'success'},
                    {'roll': 18, 'success': True, 'damage_type': 'great_success'},
                    {'roll': 20, 'success': True, 'damage_type': 'outstanding_success'}
                ]
            },
            {
                'action': ParsedAction(
                    actor="Gimli",
                    action="persuade the merchant",
                    target="merchant",
                    action_type=ActionType.SOCIAL,
                    subject="lower prices"
                ),
                'scenarios': [
                    {'roll': 6, 'success': False, 'damage_type': 'failure'},
                    {'roll': 12, 'success': True, 'damage_type': 'success'},
                    {'roll': 17, 'success': True, 'damage_type': 'great_success'}
                ]
            },
            {
                'action': ParsedAction(
                    actor="Frodo",
                    action="climb the wall",
                    target="wall",
                    action_type=ActionType.MOVEMENT
                ),
                'scenarios': [
                    {'roll': 8, 'success': False, 'damage_type': 'failure'},
                    {'roll': 14, 'success': True, 'damage_type': 'success'}
                ]
            }
        ]
    
    def load_pygmalion(self, model_path: str = None, adapter_path: str = None) -> bool:
        """Load Pygmalion narrator"""
        try:
            if model_path or adapter_path:
                self.narrators['pygmalion'] = PygmalionNarrator(
                    model_name=model_path or "PygmalionAI/pygmalion-2-7b",
                    adapter_path=adapter_path
                )
            else:
                self.narrators['pygmalion'] = PygmalionNarrator()
            
            success = self.narrators['pygmalion'].load_model()
            if success:
                print(f"[+] Pygmalion narrator loaded successfully")
            else:
                print(f"[-] Pygmalion narrator failed to load")
                self.narrators['pygmalion'] = None
            return success
        except Exception as e:
            print(f"[-] Error loading Pygmalion: {e}")
            self.narrators['pygmalion'] = None
            return False
    
    def test_single_narration(self, action: ParsedAction, dice_roll: int, success: bool, 
                            damage_type: str, narrator_name: str = 'auto') -> str:
        """Test a single narration with specified narrator"""
        if narrator_name == 'auto':
            # Use Pygmalion if available, otherwise mock
            narrator_name = 'pygmalion' if self.narrators['pygmalion'] else 'mock'
        
        narrator = self.narrators.get(narrator_name)
        if not narrator:
            print(f"[-] Narrator '{narrator_name}' not available, using mock")
            narrator = self.narrators['mock']
        
        print(f"\n{'='*60}")
        print(f"Action: {action.actor} performs {action.action}")
        print(f"Target: {action.target}")
        print(f"Type: {action.action_type.value}")
        print(f"Narrator: {narrator_name}")
        print(f"Roll: {dice_roll}, Success: {success}, Damage: {damage_type}")
        print(f"{'='*60}")
        
        try:
            narration = narrator.generate_narration(action, dice_roll, success, damage_type)
            print(f"Narration: {narration}")
            return narration
        except Exception as e:
            print(f"[-] Narration failed: {e}")
            return "The action occurs."
    
    def compare_narrators(self, action: ParsedAction, dice_roll: int, success: bool, 
                         damage_type: str) -> dict:
        """Compare results from different narrators"""
        results = {}
        
        print(f"\n{'='*70}")
        print(f"NARRATOR COMPARISON")
        print(f"Action: {action.actor} performs {action.action} against {action.target}")
        print(f"Roll: {dice_roll}, Success: {success}, Damage: {damage_type}")
        print(f"{'='*70}")
        
        for name, narrator in self.narrators.items():
            if narrator:
                try:
                    print(f"\n--- {name.upper()} NARRATOR ---")
                    narration = narrator.generate_narration(action, dice_roll, success, damage_type)
                    results[name] = narration
                    print(f"Result: {narration}")
                except Exception as e:
                    print(f"[-] {name} narrator failed: {e}")
                    results[name] = None
        
        return results
    
    def run_batch_tests(self, narrator_name: str = 'auto') -> List[str]:
        """Run all test cases"""
        print(f"\n{'='*70}")
        print(f"BATCH TESTING - Narrator: {narrator_name}")
        print(f"{'='*70}")
        
        results = []
        test_num = 1
        
        for test_case in self.test_cases:
            action = test_case['action']
            print(f"\n{'='*50}")
            print(f"Test Group {len(results) + 1}: {action.actor} - {action.action_type.value}")
            print(f"{'='*50}")
            
            for scenario in test_case['scenarios']:
                print(f"\n--- Scenario {test_num} ---")
                narration = self.test_single_narration(
                    action, 
                    scenario['roll'], 
                    scenario['success'], 
                    scenario['damage_type'],
                    narrator_name
                )
                results.append(narration)
                test_num += 1
        
        print(f"\n{'='*70}")
        print(f"BATCH TESTING COMPLETE - {len(results)} tests run")
        print(f"{'='*70}")
        
        return results
    
    def interactive_mode(self):
        """Interactive testing mode"""
        print(f"\n{'='*70}")
        print("INTERACTIVE NARRATOR TESTING")
        print("Commands:")
        print("  'pygmalion' - Switch to Pygmalion narrator")
        print("  'mock' - Switch to mock narrator")
        print("  'compare' - Compare narrators on next input")
        print("  'batch' - Run batch tests")
        print("  'load <model_path> [adapter_path]' - Load Pygmalion from paths")
        print("  'test <preset>' - Use preset action (thorin, gandalf, legolas, gimli, frodo)")
        print("  'quit' - Exit")
        print(f"{'='*70}")
        
        current_narrator = 'pygmalion' if self.narrators['pygmalion'] else 'mock'
        compare_mode = False
        
        print(f"Current narrator: {current_narrator}")
        
        while True:
            try:
                user_input = input(f"\n[{current_narrator}] Command or action: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif user_input.lower() == 'pygmalion':
                    if self.narrators['pygmalion']:
                        current_narrator = 'pygmalion'
                        print("Switched to Pygmalion narrator")
                    else:
                        print("Pygmalion narrator not loaded")
                    continue
                elif user_input.lower() == 'mock':
                    current_narrator = 'mock'
                    print("Switched to mock narrator")
                    continue
                elif user_input.lower() == 'compare':
                    compare_mode = not compare_mode
                    print(f"Compare mode: {'ON' if compare_mode else 'OFF'}")
                    continue
                elif user_input.lower() == 'batch':
                    self.run_batch_tests(current_narrator)
                    continue
                elif user_input.lower().startswith('load '):
                    parts = user_input[5:].strip().split()
                    model_path = parts[0] if parts else None
                    adapter_path = parts[1] if len(parts) > 1 else None
                    if self.load_pygmalion(model_path, adapter_path):
                        current_narrator = 'pygmalion'
                    continue
                elif user_input.lower().startswith('test '):
                    preset_name = user_input[5:].strip().lower()
                    preset_map = {
                        'thorin': 0, 'gandalf': 1, 'legolas': 2, 'gimli': 3, 'frodo': 4
                    }
                    if preset_name in preset_map:
                        test_case = self.test_cases[preset_map[preset_name]]
                        action = test_case['action']
                        print(f"Using preset: {action.actor} - {action.action}")
                        
                        # Get roll and determine outcome
                        roll_input = input("Dice roll (1-20, or press enter for random scenarios): ").strip()
                        if roll_input:
                            try:
                                dice_roll = int(roll_input)
                                success = dice_roll >= 12  # Simple success threshold
                                if dice_roll >= 20:
                                    damage_type = 'critical' if action.action_type == ActionType.ATTACK else 'outstanding_success'
                                elif dice_roll >= 18:
                                    damage_type = 'wound' if action.action_type == ActionType.ATTACK else 'great_success'
                                elif success:
                                    damage_type = 'wound' if action.action_type == ActionType.ATTACK else 'success'
                                else:
                                    damage_type = 'miss' if action.action_type == ActionType.ATTACK else 'failure'
                                
                                if compare_mode:
                                    self.compare_narrators(action, dice_roll, success, damage_type)
                                else:
                                    self.test_single_narration(action, dice_roll, success, damage_type, current_narrator)
                            except ValueError:
                                print("Invalid roll, using random scenarios")
                                for scenario in test_case['scenarios']:
                                    self.test_single_narration(
                                        action, scenario['roll'], scenario['success'], 
                                        scenario['damage_type'], current_narrator
                                    )
                        else:
                            # Run all scenarios for this preset
                            for scenario in test_case['scenarios']:
                                if compare_mode:
                                    self.compare_narrators(
                                        action, scenario['roll'], scenario['success'], scenario['damage_type']
                                    )
                                else:
                                    self.test_single_narration(
                                        action, scenario['roll'], scenario['success'], 
                                        scenario['damage_type'], current_narrator
                                    )
                    else:
                        print("Unknown preset. Available: thorin, gandalf, legolas, gimli, frodo")
                    continue
                elif not user_input:
                    continue
                
                # Parse custom action input
                print("Custom action mode - enter details:")
                actor = input("Actor name: ").strip() or "player"
                action_desc = user_input  # Use the input as action description
                target = input("Target: ").strip() or "target"
                
                # Get action type
                action_type_input = input("Action type (attack/spell/skill_check/social/movement/interact): ").strip().lower()
                action_type_map = {
                    'attack': ActionType.ATTACK,
                    'spell': ActionType.SPELL,
                    'skill_check': ActionType.SKILL_CHECK,
                    'skill': ActionType.SKILL_CHECK,
                    'social': ActionType.SOCIAL,
                    'movement': ActionType.MOVEMENT,
                    'move': ActionType.MOVEMENT,
                    'interact': ActionType.INTERACT
                }
                action_type = action_type_map.get(action_type_input, ActionType.SKILL_CHECK)
                
                # Create action
                action = ParsedAction(
                    actor=actor,
                    action=action_desc,
                    target=target,
                    action_type=action_type
                )
                
                # Get dice roll
                try:
                    dice_roll = int(input("Dice roll (1-20): ") or "10")
                    dice_roll = max(1, min(20, dice_roll))  # Clamp to 1-20
                except ValueError:
                    dice_roll = 10
                
                # Determine success and damage type
                success = dice_roll >= 12
                if dice_roll >= 20:
                    damage_type = 'critical' if action_type == ActionType.ATTACK else 'outstanding_success'
                elif dice_roll >= 18:
                    damage_type = 'wound' if action_type == ActionType.ATTACK else 'great_success'
                elif success:
                    damage_type = 'wound' if action_type == ActionType.ATTACK else 'success'
                else:
                    damage_type = 'miss' if action_type == ActionType.ATTACK else 'failure'
                
                # Generate narration
                if compare_mode:
                    self.compare_narrators(action, dice_roll, success, damage_type)
                else:
                    self.test_single_narration(action, dice_roll, success, damage_type, current_narrator)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Test D&D action narrators")
    parser.add_argument('--pygmalion-model', help='Path to Pygmalion base model')
    parser.add_argument('--pygmalion-adapter', help='Path to Pygmalion LoRA adapter')
    parser.add_argument('--narrator', choices=['pygmalion', 'mock', 'auto'], 
                       default='auto', help='Narrator to use')
    parser.add_argument('--batch', action='store_true', help='Run batch tests')
    parser.add_argument('--compare', action='store_true', help='Compare narrators')
    parser.add_argument('--preset', choices=['thorin', 'gandalf', 'legolas', 'gimli', 'frodo'],
                       help='Use preset action')
    parser.add_argument('--roll', type=int, help='Dice roll (1-20)')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = NarratorTester()
    
    # Load Pygmalion if paths provided
    if args.pygmalion_model or args.pygmalion_adapter:
        tester.load_pygmalion(args.pygmalion_model, args.pygmalion_adapter)
    else:
        tester.load_pygmalion()  # Try default paths
    
    # Handle different modes
    if args.preset:
        # Preset action mode
        preset_map = {
            'thorin': 0, 'gandalf': 1, 'legolas': 2, 'gimli': 3, 'frodo': 4
        }
        test_case = tester.test_cases[preset_map[args.preset]]
        action = test_case['action']
        
        if args.roll:
            # Single roll test
            dice_roll = max(1, min(20, args.roll))
            success = dice_roll >= 12
            if dice_roll >= 20:
                damage_type = 'critical' if action.action_type == ActionType.ATTACK else 'outstanding_success'
            elif dice_roll >= 18:
                damage_type = 'wound' if action.action_type == ActionType.ATTACK else 'great_success'
            elif success:
                damage_type = 'wound' if action.action_type == ActionType.ATTACK else 'success'
            else:
                damage_type = 'miss' if action.action_type == ActionType.ATTACK else 'failure'
            
            if args.compare:
                tester.compare_narrators(action, dice_roll, success, damage_type)
            else:
                tester.test_single_narration(action, dice_roll, success, damage_type, args.narrator)
        else:
            # Run all scenarios for this preset
            for scenario in test_case['scenarios']:
                if args.compare:
                    tester.compare_narrators(
                        action, scenario['roll'], scenario['success'], scenario['damage_type']
                    )
                else:
                    tester.test_single_narration(
                        action, scenario['roll'], scenario['success'], 
                        scenario['damage_type'], args.narrator
                    )
    elif args.batch:
        # Batch test mode
        tester.run_batch_tests(args.narrator)
    else:
        # Interactive mode
        tester.interactive_mode()


if __name__ == "__main__":
    main()