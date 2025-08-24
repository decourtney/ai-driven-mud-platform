#!/usr/bin/env python3
"""
Lightweight server testing script for the D&D narrator system.
Tests server endpoints without loading local models to save resources.
"""

import sys
import argparse
import requests
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class TestResult:
    """Container for test results"""
    input_text: str
    response_time: float
    success: bool
    response_data: Optional[Dict]
    error: Optional[str] = None


class ServerTester:
    """Lightweight testing utility for D&D narrator server"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        
        # Test prompts organized by type
        self.test_prompts = {
            'basic_attacks': [
                "I attack the goblin with my sword",
                "Hit the orc with my axe", 
                "Strike the dragon",
                "Shoot the bandit with my bow"
            ],
            'spell_casting': [
                "I cast fireball at the group of enemies",
                "Cast healing light on my ally",
                "Use magic missile against the wizard"
            ],
            'skill_checks': [
                "I try to sneak past the guards",
                "Attempt to climb the castle wall",
                "I search for traps in the chest"
            ],
            'social_interactions': [
                "I try to persuade the merchant to lower his prices",
                "Intimidate the bandit into telling us information"
            ],
            'complex_actions': [
                "I carefully examine the ancient rune while trying to avoid triggering any magical traps",
                "Cast a protection spell on myself then charge at the orc chieftain"
            ]
        }
    
    def test_server_status(self) -> bool:
        """Check if server is running and responsive"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def test_full_pipeline(self, input_text: str) -> TestResult:
        """Test the complete server pipeline"""
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.server_url}/process_input",
                json={"user_input": input_text},
                timeout=120
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return TestResult(
                    input_text=input_text,
                    response_time=response_time,
                    success=True,
                    response_data=response.json()
                )
            else:
                return TestResult(
                    input_text=input_text,
                    response_time=response_time,
                    success=False,
                    response_data=None,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
        
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                input_text=input_text,
                response_time=response_time,
                success=False,
                response_data=None,
                error=str(e)
            )
    
    def test_parser_only(self, input_text: str) -> TestResult:
        """Test just the parser endpoint"""
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.server_url}/process_user_input",
                json={"user_input": input_text},
                timeout=60
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return TestResult(
                    input_text=input_text,
                    response_time=response_time,
                    success=True,
                    response_data=response.json()
                )
            else:
                return TestResult(
                    input_text=input_text,
                    response_time=response_time,
                    success=False,
                    response_data=None,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
        
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                input_text=input_text,
                response_time=response_time,
                success=False,
                response_data=None,
                error=str(e)
            )
    
    def test_narrator_only(self, parsed_action_json: Dict, hit: bool = True, damage_type: str = "wound") -> TestResult:
        """Test just the narrator endpoint with structured JSON input"""
        start_time = time.time()
        
        try:
            payload = {
                "parsed_action": parsed_action_json,
                "hit": hit,
                "damage_type": damage_type
            }
            
            response = requests.post(
                f"{self.server_url}/process_structured_action",
                json=payload,
                timeout=60
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return TestResult(
                    input_text=f"Narration for: {parsed_action_json}",
                    response_time=response_time,
                    success=True,
                    response_data=response.json()
                )
            else:
                return TestResult(
                    input_text=f"Narration for: {parsed_action_json}",
                    response_time=response_time,
                    success=False,
                    response_data=None,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
        
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                input_text=f"Narration for: {parsed_action_json}",
                response_time=response_time,
                success=False,
                response_data=None,
                error=str(e)
            )
    
    def print_result(self, result: TestResult, show_details: bool = True):
        """Pretty print a test result"""
        print(f"\n{'='*80}")
        print(f"INPUT: {result.input_text}")
        print(f"{'='*80}")
        
        if result.error:
            print(f"ERROR: {result.error}")
            return
        
        print(f"Response Time: {result.response_time:.3f}s")
        print(f"Success: {'Yes' if result.success else 'No'}")
        
        if result.response_data and show_details:
            print(f"\nResponse Data:")
            print(json.dumps(result.response_data, indent=2))
    
    def print_pipeline_result(self, result: TestResult):
        """Pretty print a full pipeline result with D&D formatting"""
        print(f"\n{'='*80}")
        print(f"INPUT: {result.input_text}")
        print(f"{'='*80}")
        
        if result.error:
            print(f"ERROR: {result.error}")
            return
        
        print(f"Response Time: {result.response_time:.3f}s")
        
        if result.response_data:
            data = result.response_data
            
            print(f"\nPARSED ACTION:")
            print(f"  Actor: {data.get('actor', 'unknown')}")
            print(f"  Action: {data.get('action', 'unknown')}")
            print(f"  Target: {data.get('target', 'None')}")
            print(f"  Type: {data.get('action_type', 'unknown')}")
            print(f"  Weapon: {data.get('weapon', 'None')}")
            print(f"  Subject: {data.get('subject', 'None')}")
            print(f"  Details: {data.get('details', 'None')}")
            print(f"  Parsing Method: {data.get('parsing_method', 'Unknown')}")
            
            print(f"\nOUTCOME:")
            print(f"  Dice Roll: {data.get('dice_roll', 0)}")
            print(f"  Hit: {'Yes' if data.get('hit', False) else 'No'}")
            print(f"  Damage Type: {data.get('damage_type', 'unknown')}")
            
            print(f"\nNARRATION:")
            print(f"  {data.get('narration', 'No narration provided')}")
    
    def run_batch_tests(self, category: str = 'all'):
        """Run batch tests on server"""
        print(f"\n{'='*100}")
        print(f"BATCH TESTING - Category: {category.upper()}")
        print(f"{'='*100}")
        
        if not self.test_server_status():
            print("ERROR: Server is not responding. Make sure it's running.")
            return
        
        # Select test prompts
        if category == 'all':
            all_prompts = []
            for cat, prompts in self.test_prompts.items():
                all_prompts.extend(prompts)
            test_prompts = all_prompts
        elif category in self.test_prompts:
            test_prompts = self.test_prompts[category]
        else:
            print(f"Unknown category: {category}")
            return
        
        results = []
        total_time = 0
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n[{i}/{len(test_prompts)}] Testing: {prompt}")
            
            result = self.test_full_pipeline(prompt)
            results.append(result)
            total_time += result.response_time
            
            # Show brief result
            if result.error:
                print(f"   ERROR: {result.error}")
            elif result.response_data:
                data = result.response_data
                print(f"   Time: {result.response_time:.3f}s | Roll: {data.get('dice_roll', 0)} | Hit: {'Yes' if data.get('hit', False) else 'No'}")
                narration = data.get('narration', '')
                print(f"   Narration: {narration[:100]}{'...' if len(narration) > 100 else ''}")
        
        # Summary
        successful = len([r for r in results if r.hit])
        failed = len(results) - successful
        avg_time = total_time / len(results) if results else 0
        
        print(f"\n{'='*100}")
        print(f"BATCH SUMMARY")
        print(f"{'='*100}")
        print(f"Total Tests: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {successful/len(results)*100:.1f}%")
        print(f"Total Time: {total_time:.3f}s")
        print(f"Average Time: {avg_time:.3f}s per test")
    
    def interactive_menu(self):
        """Interactive testing menu"""
        print(f"\n{'='*100}")
        print("D&D SERVER TESTING MENU")
        print("="*100)
        print("1. Test Full Pipeline (input -> complete game turn)")
        print("2. Test Parser Only (input -> parsed action)")
        print("3. Test Narrator Only (structured action -> narration)")
        print("4. Run Batch Tests")
        print("5. Check Server Status")
        print("6. Exit")
        print(f"Server URL: {self.server_url}")
        print(f"Categories: {', '.join(self.test_prompts.keys())}")
        print("="*100)
        
        while True:
            try:
                choice = input("\nSelect option (1-6): ").strip()
                
                if choice == '1':
                    # Full pipeline test
                    user_input = input("Enter action to test: ").strip()
                    if user_input:
                        result = self.test_full_pipeline(user_input)
                        self.print_pipeline_result(result)
                
                elif choice == '2':
                    # Parser only test
                    user_input = input("Enter action to parse: ").strip()
                    if user_input:
                        result = self.test_parser_only(user_input)
                        self.print_result(result)
                
                elif choice == '3':
                    # Narrator only test
                    print("\nEnter parsed action JSON (or press Enter for example):")
                    json_input = input().strip()
                    
                    if not json_input:
                        # Provide example
                        json_input = '''{
                            "actor": "player",
                            "action": "sword strike",
                            "target": "goblin",
                            "action_type": "attack",
                            "weapon": "sword",
                            "subject": null,
                            "details": null
                        }'''
                        print(f"Using example: {json_input}")
                    
                    try:
                        parsed_action = json.loads(json_input)
                        
                        hit = input("Hit? (y/n, default y): ").strip().lower()
                        hit = hit != 'n'
                        
                        damage_type = input("Damage type (wound/critical/kill/miss, default wound): ").strip()
                        damage_type = damage_type if damage_type else "wound"
                        
                        result = self.test_narrator_only(parsed_action, hit, damage_type)
                        self.print_result(result)
                        
                    except json.JSONDecodeError as e:
                        print(f"Invalid JSON: {e}")
                
                elif choice == '4':
                    # Batch tests
                    print(f"\nAvailable categories: {', '.join(self.test_prompts.keys())}, all")
                    category = input("Enter category (default 'all'): ").strip()
                    category = category if category else 'all'
                    self.run_batch_tests(category)
                
                elif choice == '5':
                    # Server status
                    if self.test_server_status():
                        print("Server is running and responsive")
                    else:
                        print("Server is not responding")
                
                elif choice == '6':
                    print("Exiting...")
                    break
                
                else:
                    print("Invalid option. Please select 1-6.")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="D&D narrator server testing utility")
    parser.add_argument('--server-url', default='http://localhost:8000', 
                       help='Server URL (default: http://localhost:8000)')
    parser.add_argument('--mode', choices=['menu', 'batch', 'single'], 
                       default='menu', help='Testing mode')
    parser.add_argument('--category', choices=['basic_attacks', 'spell_casting', 'skill_checks', 
                                              'social_interactions', 'complex_actions', 'all'], 
                       default='all', help='Category for batch tests')
    parser.add_argument('input', nargs='?', help='Single input to test')
    
    args = parser.parse_args()
    
    tester = ServerTester(args.server_url)
    
    try:
        if args.mode == 'single' and args.input:
            # Single test
            result = tester.test_full_pipeline(args.input)
            tester.print_pipeline_result(result)
        elif args.mode == 'batch':
            # Batch tests
            tester.run_batch_tests(args.category)
        else:
            # Interactive menu (default)
            tester.interactive_menu()
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
