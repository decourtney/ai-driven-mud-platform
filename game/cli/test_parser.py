#!/usr/bin/env python3
"""
Standalone parser testing tool.
Allows testing different parsers in isolation without loading other components.
"""

import sys
import argparse
from typing import List

# Add parent directory to path for imports
sys.path.append('..')

from game.parsers.codellama_parser import CodeLlamaParser
from game.parsers.fallback_parser import FallbackParser
from game.core.models import ParsedAction


class ParserTester:
    """Interactive parser testing utility"""
    
    def __init__(self):
        self.parsers = {
            'codellama': None,
            'fallback': FallbackParser()
        }
        
        # Load fallback parser (always available)
        self.parsers['fallback'].load_model()
        
        # Test cases for batch testing
        self.test_cases = [
            "I attack the goblin with my sword",
            "Cast fireball at the orc", 
            "I try to sneak past the guard",
            "ask the barkeep about brown elf",
            "tell the merchant about the ancient ruins",
            "I want to bargain with the merchant",
            "I steal the gem from the chest",
            "I climb the wall",
            "I open the door carefully",
            "I examine the chest for traps",
            "I talk to the innkeeper about rooms",
            "I run towards the exit",
            "Promise death to anyone that crosses me",
            "I investigate the mysterious symbol",
            "Heal the wounded ally with magic"
        ]
    
    def load_codellama(self, model_path: str = None) -> bool:
        """Load CodeLlama parser"""
        try:
            if model_path:
                self.parsers['codellama'] = CodeLlamaParser(model_path)
            else:
                self.parsers['codellama'] = CodeLlamaParser()
            
            success = self.parsers['codellama'].load_model()
            if success:
                print(f"[+] CodeLlama parser loaded successfully")
            else:
                print(f"[-] CodeLlama parser failed to load")
                self.parsers['codellama'] = None
            return success
        except Exception as e:
            print(f"[-] Error loading CodeLlama: {e}")
            self.parsers['codellama'] = None
            return False
    
    def test_single_input(self, text: str, parser_name: str = 'auto', context: str = "") -> ParsedAction:
        """Test a single input with specified parser"""
        if parser_name == 'auto':
            # Use CodeLlama if available, otherwise fallback
            parser_name = 'codellama' if self.parsers['codellama'] else 'fallback'
        
        parser = self.parsers.get(parser_name)
        if not parser:
            print(f"[-] Parser '{parser_name}' not available, using fallback")
            parser = self.parsers['fallback']
        
        print(f"\n{'='*50}")
        print(f"Input: '{text}'")
        print(f"Parser: {parser_name}")
        if context:
            print(f"Context: '{context}'")
        print(f"{'='*50}")
        
        try:
            result = parser.parse_action(text, context)
            self._print_parsed_action(result)
            return result
        except Exception as e:
            print(f"[-] Parsing failed: {e}")
            return None
    
    def compare_parsers(self, text: str, context: str = "") -> dict:
        """Compare results from different parsers"""
        results = {}
        
        print(f"\n{'='*60}")
        print(f"PARSER COMPARISON")
        print(f"Input: '{text}'")
        if context:
            print(f"Context: '{context}'")
        print(f"{'='*60}")
        
        for name, parser in self.parsers.items():
            if parser:
                try:
                    print(f"\n--- {name.upper()} PARSER ---")
                    result = parser.parse_action(text, context)
                    results[name] = result
                    self._print_parsed_action(result)
                except Exception as e:
                    print(f"[-] {name} parser failed: {e}")
                    results[name] = None
        
        return results
    
    def run_batch_tests(self, parser_name: str = 'auto') -> List[ParsedAction]:
        """Run all test cases"""
        print(f"\n{'='*60}")
        print(f"BATCH TESTING - Parser: {parser_name}")
        print(f"{'='*60}")
        
        results = []
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n--- Test Case {i}/{len(self.test_cases)} ---")
            result = self.test_single_input(test_case, parser_name)
            results.append(result)
        
        return results
    
    def interactive_mode(self):
        """Interactive testing mode"""
        print(f"\n{'='*60}")
        print("INTERACTIVE PARSER TESTING")
        print("Commands:")
        print("  'codellama' - Switch to CodeLlama parser")
        print("  'fallback' - Switch to fallback parser")
        print("  'compare <text>' - Compare parsers on input")
        print("  'batch' - Run batch tests")
        print("  'load <path>' - Load CodeLlama from path")
        print("  'quit' - Exit")
        print(f"{'='*60}")
        
        current_parser = 'codellama' if self.parsers['codellama'] else 'fallback'
        print(f"Current parser: {current_parser}")
        
        while True:
            try:
                user_input = input(f"\n[{current_parser}] Enter D&D action: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif user_input.lower() == 'codellama':
                    if self.parsers['codellama']:
                        current_parser = 'codellama'
                        print("Switched to CodeLlama parser")
                    else:
                        print("CodeLlama parser not loaded")
                    continue
                elif user_input.lower() == 'fallback':
                    current_parser = 'fallback'
                    print("Switched to fallback parser")
                    continue
                elif user_input.lower().startswith('compare '):
                    text = user_input[8:].strip()
                    if text:
                        self.compare_parsers(text)
                    continue
                elif user_input.lower() == 'batch':
                    self.run_batch_tests(current_parser)
                    continue
                elif user_input.lower().startswith('load '):
                    path = user_input[5:].strip()
                    if self.load_codellama(path):
                        current_parser = 'codellama'
                    continue
                elif not user_input:
                    continue
                
                # Parse the input
                self.test_single_input(user_input, current_parser)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def _print_parsed_action(self, action: ParsedAction):
        """Pretty print a parsed action"""
        if not action:
            print("[-] No result")
            return
        
        print(f"✓ Actor: {action.actor}")
        print(f"✓ Action: {action.action}")
        print(f"✓ Target: {action.target or 'None'}")
        print(f"✓ Type: {action.action_type.value}")
        print(f"✓ Weapon: {action.weapon or 'None'}")
        print(f"✓ Subject: {action.subject or 'None'}")
        print(f"✓ Details: {action.details or 'None'}")
        print(f"✓ Method: {action.parsing_method or 'Unknown'}")


def main():
    parser = argparse.ArgumentParser(description="Test D&D action parsers")
    parser.add_argument('--codellama-path', help='Path to CodeLlama model')
    parser.add_argument('--parser', choices=['codellama', 'fallback', 'auto'], 
                       default='auto', help='Parser to use')
    parser.add_argument('--batch', action='store_true', help='Run batch tests')
    parser.add_argument('--compare', action='store_true', help='Compare all parsers')
    parser.add_argument('text', nargs='?', help='Text to parse')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = ParserTester()
    
    # Load CodeLlama if path provided
    if args.codellama_path:
        tester.load_codellama(args.codellama_path)
    else:
        tester.load_codellama()  # Try default path
    
    # Handle different modes
    if args.text:
        # Single input mode
        if args.compare:
            tester.compare_parsers(args.text)
        else:
            tester.test_single_input(args.text, args.parser)
    elif args.batch:
        # Batch test mode
        tester.run_batch_tests(args.parser)
    else:
        # Interactive mode
        tester.interactive_mode()


if __name__ == "__main__":
    main()