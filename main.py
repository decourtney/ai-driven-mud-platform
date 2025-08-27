#!/usr/bin/env python3
"""
Main entry point for the D&D Streaming Game Engine.
Supports both server mode for Next.js frontend and CLI testing modes.
"""

import argparse
import sys
import threading
import uuid
from typing import Optional

from api.server import create_server
from cli.test_parser import ParserTester
from core.game_engine import GameEngine, GameCondition
from core.model_manager import ModelManager
from core.character_state import CharacterState


def run_server_mode(args):
    """Run the FastAPI server optimized for Next.js frontend"""
    print("[+] Starting D&D Streaming Game Server for Next.js...")
    
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
        print(f"[+] Ready for Next.js frontend connections on http://{args.host}:{args.port}")
    else:
        print("[-] Warning: Failed to load models")
        print("[-] Models will auto-load on first request")
    
    # Add CLI thread if requested (for debugging)
    if args.with_cli:
        def cli_loop():
            print("\n[+] Server CLI mode active")
            print("Commands: '/sessions' - list sessions, '/reload' - reload models, '/status' - check status, '/quit' - shutdown")
            
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
                        status = {
                            "models_loaded": server.model_manager.are_models_loaded(),
                            "active_sessions": len(server.active_sessions),
                            "parser_ready": server.model_manager.is_parser_ready(),
                            "narrator_ready": server.model_manager.is_narrator_ready()
                        }
                        print(f"Status: {status}")
                        if server.model_manager.are_models_loaded():
                            memory = server.model_manager.get_memory_usage()
                            print(f"GPU memory: {memory}")
                    elif cmd.lower() == '/sessions':
                        print(f"Active sessions: {len(server.active_sessions)}")
                        for session_id, session in server.active_sessions.items():
                            print(f"  - {session_id}: {session.player_name} ({session.game_condition.value})")
                    elif cmd.lower() == '/unload':
                        server.model_manager.unload_all_models()
                        print("Models unloaded")
                    else:
                        print("Available commands: /sessions, /reload, /status, /unload, /quit")
                        
                except KeyboardInterrupt:
                    print("\nShutting down server...")
                    sys.exit(0)
                except Exception as e:
                    print(f"CLI Error: {e}")
        
        threading.Thread(target=cli_loop, daemon=True).start()
    
    server.run(host=args.host, port=args.port)


def run_streaming_game_mode(args):
    """Run the streaming game engine in CLI mode for testing"""
    print("[+] Starting Streaming Game Engine CLI Mode...")
    
    # Initialize components
    model_manager = ModelManager()
    
    print("[+] Loading models...")
    if not model_manager.load_all_models():
        print("[-] Failed to load models. Exiting.")
        return
    
    print("[+] Models loaded successfully!")
    
    # Create game engine
    engine = GameEngine(model_manager)
    
    # Set up game state
    player_name = args.player_name or "Hero"
    print(f"[+] Creating game for player: {player_name}")
    
    player = CharacterState(
        name=player_name,
        max_hp=20,
        current_hp=20,
        equipped_weapon="sword"
    )
    
    npcs = [
        CharacterState(name="vampire", max_hp=8, current_hp=8, equipped_weapon="Sharp Fangs"),
        # CharacterState(name="Orc", max_hp=15, current_hp=15, equipped_weapon="axe")
    ]
    
    scene_state = {
        "name": "Test Dungeon",
        "description": "A dark stone chamber with flickering torches",
        "rules": {},
        "difficulty_modifier": 0
    }
    
    engine.initialize_game_state(player, npcs, scene_state)
    
    print(f"[+] Game initialized! Type 'help' for commands or describe your actions.")
    print("="*60)
    
    # Display initial scene
    scene = engine.get_current_scene()
    print(f"\n🎭 SCENE: {scene}\n")
    
    # Game loop
    while True:
        try:
            user_input = input(f"{player_name}> ").strip()
            
            if not user_input:
                continue
                
            # Special commands
            if user_input.lower() in ['quit', 'exit']:
                break
            elif user_input.lower() == 'help':
                print("\nCommands:")
                print("  help - Show this help")
                print("  status - Show character status")
                print("  scene - Show current scene")
                print("  quit/exit - Exit game")
                print("\nOr describe any action you want to take!")
                continue
            elif user_input.lower() == 'status':
                state = engine.game_state
                print(f"\n📊 STATUS:")
                print(f"Player: {state.player.name} ({state.player.current_hp}/{state.player.max_hp} HP)")
                for npc in state.npcs:
                    status = "alive" if npc.is_alive() else "defeated"
                    print(f"  {npc.name}: {npc.current_hp}/{npc.max_hp} HP ({status})")
                print(f"Turn: {state.turn_counter}\n")
                continue
            elif user_input.lower() == 'scene':
                scene = engine.get_current_scene()
                print(f"\n🎭 SCENE: {scene}\n")
                continue
            
            print(f"\n⚡ Processing action: '{user_input}'")
            
            # Process player action immediately
            print("🎲 Rolling dice and generating result...")
            player_narration, condition = engine.execute_player_turn(user_input)
            
            print(f"📖 {player_narration}")
            
            # Check game condition
            if condition != GameCondition.CONTINUE:
                print(f"\n🎮 GAME OVER: {condition.value}")
                break
                
            if not should_continue:
                print("❌ Action failed. Try again.")
                continue
            
            # Process NPCs
            print("\n⏳ NPCs are taking their turns...")
            living_npcs = engine.get_living_npcs()
            
            if living_npcs:
                for npc in living_npcs:
                    print(f"  🤖 {npc.name} is deciding...")
                    
                    npc_narration, success = engine.process_single_npc_action(npc)
                    if npc_narration:
                        print(f"  📖 {npc_narration}")
                    
                    # Check condition after each NPC
                    current_condition = engine.check_game_condition()
                    if current_condition != GameCondition.CONTINUE:
                        print(f"\n🎮 GAME OVER: {current_condition.value}")
                        return
            else:
                print("  (No living NPCs to act)")
            
            # Update scene
            print("\n🔄 Updating scene...")
            scene_description, final_condition = engine.get_updated_scene_after_actions()
            
            print(f"\n🎭 UPDATED SCENE: {scene_description}")
            
            # Final condition check
            if final_condition != GameCondition.CONTINUE:
                print(f"\n🎮 GAME OVER: {final_condition.value}")
                break
            
            print("\n" + "="*60)
            
        except KeyboardInterrupt:
            print("\n\nGame interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Try again or type 'help' for commands.")


def run_test_parser_mode(args):
    """Run parser testing mode (unchanged from original)"""
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


def run_quick_test_mode(args):
    """Quick test mode with new streaming engine"""
    print(f"[+] Quick streaming test: '{args.text}'")
    
    # Initialize minimal components
    model_manager = ModelManager()
    
    print("[+] Loading models...")
    if not model_manager.load_all_models():
        print("[-] Failed to load models")
        return
    
    # Create engine and minimal game state
    engine = GameEngine(model_manager)
    
    player = CharacterState(name="TestPlayer", max_hp=20, current_hp=20, equipped_weapon="sword")
    npcs = [CharacterState(name="TestGoblin", max_hp=5, current_hp=5, equipped_weapon="club")]
    scene = {"name": "Test Scene", "description": "A simple test chamber", "rules": {}}
    
    engine.initialize_game_state(player, npcs, scene)
    
    # Process the test action
    print(f"[+] Processing action: {args.text}")
    
    try:
        player_narration, condition, should_continue = engine.process_player_input_immediate(args.text)
        print(f"Player result: {player_narration}")
        print(f"Game condition: {condition.value}")
        print(f"Should continue: {should_continue}")
        
        if should_continue and condition == GameCondition.CONTINUE:
            # Test one NPC action
            print("\n[+] Testing NPC response...")
            living_npcs = engine.get_living_npcs()
            if living_npcs:
                npc_narration, success = engine.process_single_npc_action(living_npcs[0])
                print(f"NPC result: {npc_narration}")
            
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Main CLI entry point with subcommands"""
    parser = argparse.ArgumentParser(
        description="D&D Streaming Game Engine - AI-powered real-time gameplay",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
          Examples:
            python main.py server --host 0.0.0.0 --port 8000  # Start server for Next.js
            python main.py game --player-name "Aragorn"       # CLI game mode
            python main.py quick "attack the goblin"          # Quick test
        """
    )
    
    subparsers = parser.add_subparsers(dest='mode', help='Operation mode')
    
    # Server mode (for Next.js frontend)
    server_parser = subparsers.add_parser('server', help='Run FastAPI server for Next.js frontend')
    server_parser.add_argument('--host', default='0.0.0.0', help='Server host')
    server_parser.add_argument('--port', type=int, default=8000, help='Server port')
    server_parser.add_argument('--parser-model', help='Path to CodeLlama parser model')
    server_parser.add_argument('--narrator-model', help='Path to narrator base model')
    server_parser.add_argument('--narrator-adapter', help='Path to narrator LoRA adapter')
    server_parser.add_argument('--with-cli', action='store_true', help='Run CLI alongside server for debugging')
    
    # Streaming game mode (CLI testing)
    game_parser = subparsers.add_parser('game', help='Run streaming game in CLI mode')
    game_parser.add_argument('--player-name', default='Hero', help='Player character name')
    game_parser.add_argument('--parser-model', help='Path to CodeLlama parser model')
    game_parser.add_argument('--narrator-model', help='Path to narrator base model')
    game_parser.add_argument('--narrator-adapter', help='Path to narrator LoRA adapter')
    
    # Parser testing mode  
    parser_parser = subparsers.add_parser('test-parser', help='Test action parsers')
    parser_parser.add_argument('--parser-model', help='Path to CodeLlama model')
    parser_parser.add_argument('--parser', choices=['codellama', 'fallback', 'auto'], 
                              default='auto', help='Parser to use')
    parser_parser.add_argument('--batch', action='store_true', help='Run batch tests')
    parser_parser.add_argument('--compare', action='store_true', help='Compare parsers')
    parser_parser.add_argument('text', nargs='?', help='Text to parse')
    
    # Quick test mode
    quick_parser = subparsers.add_parser('quick', help='Quick test with minimal setup')
    quick_parser.add_argument('text', help='Action to test')
    quick_parser.add_argument('--fallback-only', action='store_true', help='Use only fallback parser')
    
    args = parser.parse_args()
    
    # Handle no subcommand (default to server mode for Next.js)
    if not args.mode:
        print("No mode specified. Starting server for Next.js frontend...")
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
        elif args.mode == 'game':
            run_streaming_game_mode(args)
        elif args.mode == 'test-parser':
            run_test_parser_mode(args)
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