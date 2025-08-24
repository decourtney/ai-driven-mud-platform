#!/usr/bin/env python3
"""
Main entry point for the D&D Narrator system.
Provides unified CLI interface for all components.
"""

import argparse
import sys
import threading
from typing import Optional

from api.server import create_server
from cli.test_parser import ParserTester
from core.models import ProcessUserInputRequest


def run_server_mode(args):
    """Run the FastAPI server"""
    print("[+] Starting D&D Narrator Server...")
    
    server = create_server(
        parser_model_path=args.parser_model,
        narrator_model_path=args.narrator_model, 
        narrator_adapter_path=args.narrator_adapter
    )
    
    # Load models at startup
    print("[+] Loading models at startup...")
    results = server.load_all_models()
    if results["models_manager"]:
        print("[+] Models loaded successfully!")
    else:
        print("[-] Warning: Failed to load models")
        print("[-] Models will auto-load on first request")
    
    # Add CLI thread if requested
    if args.with_cli:
        def cli_loop():
            print("\n[+] CLI mode active alongside server")
            print("Commands: '/reload' - reload models, '/status' - check status, '/quit' - shutdown server")
            
            while True:
                try:
                    cmd = input("\nServer CLI> ").strip()
                    
                    if cmd.lower() == '/quit':
                        print("Shutting down server...")
                        sys.exit(0)
                    elif cmd.lower() == '/reload':
                        results = server.load_all_models()
                        print(f"Reload results: {results}")
                    elif cmd.lower() == '/status':
                        status = server.game_engine.is_ready()
                        memory = server.model_manager.get_memory_usage()
                        print(f"Component status: {status}")
                        print(f"GPU memory: {memory}")
                    elif cmd.lower() == '/unload':
                        server.model_manager.unload_all_models()
                        print("Models unloaded")
                    elif cmd and not cmd.startswith('/'):
                        # Process as natural language action
                        try:
                            request = ProcessUserInputRequest(user_input=cmd)
                            result = server.game_engine.execute_game_turn(request)
                            print(f"Action: {result.parsed_action.action}")
                            print(f"Roll: {result.dice_roll}, Hit: {result.hit}")
                            print(f"Narration: {result.narration}")
                        except Exception as e:
                            print(f"Error: {e}")
                    else:
                        print("Available commands: /reload, /status, /unload, /quit")
                        print("Or enter natural language to test the system")
                        
                except KeyboardInterrupt:
                    print("\nShutting down server...")
                    sys.exit(0)
                except Exception as e:
                    print(f"CLI Error: {e}")
        
        threading.Thread(target=cli_loop, daemon=True).start()
    
    server.run(host=args.host, port=args.port)


def run_test_parser_mode(args):
    """Run parser testing mode"""
    print("[+] Starting Parser Testing Mode...")
    
    tester = ParserTester()
    
    # Load CodeLlama if path specified
    if args.parser_model:
        tester.load_codellama(args.parser_model)
    else:
        tester.load_codellama()
    
    if args.text:
        # Single test
        if args.compare:
            tester.compare_parsers(args.text)
        else:
            tester.test_single_input(args.text, args.parser)
    elif args.batch:
        # Batch tests
        tester.run_batch_tests(args.parser)
    else:
        # Interactive mode
        tester.interactive_mode()


def run_test_narrator_mode(args):
    """Run narrator testing mode"""
    print("[+] Starting Narrator Testing Mode...")
    
    # Import here to avoid loading heavy models unless needed
    from narrators.pygmalion_narrator import PygmalionNarrator
    from core.models import ParsedAction, ActionType
    
    narrator = PygmalionNarrator(
        model_name=args.narrator_model,
        adapter_path=args.narrator_adapter
    )
    
    if not narrator.load_model():
        print("[-] Failed to load narrator model")
        return
    
    print("[+] Narrator loaded successfully")
    
    # Test cases
    test_actions = [
        ParsedAction(
            actor="Thorin",
            action="sword strike", 
            target="goblin",
            action_type=ActionType.ATTACK,
            weapon="sword"
        ),
        ParsedAction(
            actor="Gandalf",
            action="fireball spell",
            target="orc",
            action_type=ActionType.SPELL
        ),
        ParsedAction(
            actor="Legolas", 
            action="stealth attempt",
            target="guard",
            action_type=ActionType.SKILL_CHECK
        )
    ]
    
    if args.interactive:
        print("\nInteractive narrator testing (type 'quit' to exit):")
        while True:
            try:
                action_text = input("\nDescribe action: ").strip()
                if action_text.lower() in ['quit', 'exit']:
                    break
                
                # Simple parsing for demo
                action = ParsedAction(
                    actor="player",
                    action=action_text,
                    target="target",
                    action_type=ActionType.ATTACK
                )
                
                dice_roll = int(input("Dice roll (1-20): ") or "10")
                hit = dice_roll >= 10
                damage_type = "critical" if dice_roll >= 18 else "wound" if hit else "miss"
                
                narration = narrator.generate_narration(action, hit, damage_type)
                print(f"Narration: {narration}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    else:
        # Run test cases
        for i, action in enumerate(test_actions, 1):
            print(f"\n--- Test Case {i} ---")
            print(f"Action: {action.actor} performs {action.action} against {action.target}")
            
            for roll in [5, 12, 18, 20]:  # Different roll outcomes
                hit = roll >= 12
                damage_type = "critical" if roll >= 18 else "wound" if hit else "miss"
                
                narration = narrator.generate_narration(action, hit, damage_type)
                print(f"Roll {roll}: {narration}")


def run_quick_test_mode(args):
    """Quick test mode using minimal components"""
    print(f"[+] Quick test: '{args.text}'")
    
    if args.fallback_only:
        from parsers.fallback_parser import FallbackParser
        parser = FallbackParser()
        parser.load_model()
        result = parser.parse_action(args.text)
        print(f"Parsed with fallback: {result}")
    else:
        # Try to use full system with ModelManager
        from core.model_manager import ModelManager
        from core.game_engine import GameEngine
        from core.models import ProcessUserInputRequest
        
        # Use ModelManager for efficient model handling
        model_manager = ModelManager()
        
        # Load models
        print("[+] Loading models...")
        if not model_manager.load_all_models():
            print("[-] Failed to load models, trying fallback parser only...")
            from parsers.fallback_parser import FallbackParser
            parser = FallbackParser()
            parser.load_model()
            result = parser.parse_action(args.text)
            print(f"Parsed with fallback: {result}")
            return
        
        engine = GameEngine(model_manager)
        request = ProcessUserInputRequest(user_input=args.text)
        
        result = engine.execute_game_turn(request)
        
        print(f"Parsed Action: {result.parsed_action.action}")
        print(f"Roll: {result.dice_roll}, Hit: {result.hit}")
        print(f"Narration: {result.narration}")


def main():
    """Main CLI entry point with subcommands"""
    parser = argparse.ArgumentParser(
        description="D&D Narrator System - AI-powered action parsing and narration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='mode', help='Operation mode')
    
    # Server mode
    server_parser = subparsers.add_parser('server', help='Run FastAPI server')
    server_parser.add_argument('--host', default='0.0.0.0', help='Server host')
    server_parser.add_argument('--port', type=int, default=8000, help='Server port')
    server_parser.add_argument('--parser-model', help='Path to CodeLlama parser model')
    server_parser.add_argument('--narrator-model', help='Path to narrator base model')
    server_parser.add_argument('--narrator-adapter', help='Path to narrator LoRA adapter')
    server_parser.add_argument('--with-cli', action='store_true', help='Run CLI alongside server')
    
    # Parser testing mode  
    parser_parser = subparsers.add_parser('test-parser', help='Test action parsers')
    parser_parser.add_argument('--parser-model', help='Path to CodeLlama model')
    parser_parser.add_argument('--parser', choices=['codellama', 'fallback', 'auto'], 
                              default='auto', help='Parser to use')
    parser_parser.add_argument('--batch', action='store_true', help='Run batch tests')
    parser_parser.add_argument('--compare', action='store_true', help='Compare parsers')
    parser_parser.add_argument('text', nargs='?', help='Text to parse')
    
    # Narrator testing mode
    narrator_parser = subparsers.add_parser('test-narrator', help='Test narration generation')
    narrator_parser.add_argument('--narrator-model', help='Path to narrator base model')
    narrator_parser.add_argument('--narrator-adapter', help='Path to narrator LoRA adapter')
    narrator_parser.add_argument('--interactive', action='store_true', help='Interactive testing mode')
    
    # Quick test mode
    quick_parser = subparsers.add_parser('quick', help='Quick test with minimal setup')
    quick_parser.add_argument('text', help='Action to test')
    quick_parser.add_argument('--fallback-only', action='store_true', help='Use only fallback parser')
    
    args = parser.parse_args()
    
    # Handle no subcommand (default to interactive server with CLI)
    if not args.mode:
        print("No mode specified. Starting server with CLI...")
        args.mode = 'server'
        args.with_cli = True
        args.host = '0.0.0.0'
        args.port = 8000
        args.parser_model = None
        args.narrator_model = None
        args.narrator_adapter = None
    
    # Route to appropriate handler
    try:
        if args.mode == 'server':
            run_server_mode(args)
        elif args.mode == 'test-parser':
            run_test_parser_mode(args)
        elif args.mode == 'test-narrator':
            run_test_narrator_mode(args)
        elif args.mode == 'quick':
            run_quick_test_mode(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()