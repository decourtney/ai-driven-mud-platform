# D&D Narrator System - Refactored Architecture

A modular AI-powered system for parsing natural language D&D actions and generating narrative descriptions.

## Architecture Overview

```
dnd_narrator/
├── core/                    # Core business logic (no dependencies on specific AI models)
│   ├── interfaces.py       # Abstract base classes for components
│   ├── models.py          # Pydantic data models
│   └── game_engine.py     # Main orchestration logic
├── parsers/               # Action parsing implementations
│   ├── codellama_parser.py # AI-powered parser using CodeLlama
│   └── fallback_parser.py # Rule-based backup parser
├── narrators/             # Narrative generation implementations
│   ├── pygmalion_narrator.py # AI narrator using Pygmalion+LoRA
│   └── mock_narrator.py      # Simple template-based narrator for testing
├── api/                   # FastAPI web service
│   └── server.py         # HTTP API endpoints
├── cli/                   # Command-line tools
│   ├── test_parser.py    # Standalone parser testing
│   └── test_narrator.py  # Standalone narrator testing
└── main.py               # Unified CLI entry point
```

## Key Improvements

### 1. **Dependency Injection**
Components are injected rather than hard-coded, making testing and swapping implementations easy:

```python
# Old way - tightly coupled
parser = CodeLlamaActionParser()  # Hard-coded in server

# New way - flexible
parser = CodeLlamaParser()  # or FallbackParser() or MockParser()
narrator = PygmalionNarrator()  # or MockNarrator()
engine = GameEngine(parser, narrator)  # Injected dependencies
```

### 2. **Interface Segregation**
Clear contracts define what each component must implement:

```python
class ActionParser(ABC):
    @abstractmethod
    def parse_action(self, user_input: str, context: str = "") -> ParsedAction:
        pass
```

### 3. **Single Responsibility**
Each module has one clear purpose:
- `GameEngine`: Orchestrates the game logic flow
- `Server`: Handles HTTP requests/responses only
- `Parsers`: Convert text to structured data only
- `Narrators`: Generate narrative text only

### 4. **Easy Testing**
Components can be tested in isolation:

```python
# Test parser without loading narrator
parser = FallbackParser()
result = parser.parse_action("attack the goblin")

# Test with mock dependencies
mock_narrator = MockNarrator()
engine = GameEngine(parser, mock_narrator)
```

## Usage Examples

### 1. **Run Full Server**
```bash
python main.py server --host 0.0.0.0 --port 8000
```

### 2. **Test Parser Only**
```bash
python main.py test-parser "I attack the dragon with my sword"
python main.py test-parser --compare "cast fireball at orc"  # Compare all parsers
python main.py test-parser --batch  # Run all test cases
```

### 3. **Quick Test with Minimal Setup**
```bash
python main.py quick "sneak past the guard"
```

### 4. **Interactive Server with CLI**
```bash
python main.py  # Defaults to server with CLI enabled
```

### 5. **API Usage**
```python
import requests

# Process natural language
response = requests.post("http://localhost:8000/process_action", json={
    "player_input": "I cast fireball at the goblin",
    "scene_context": "dark dungeon",
    "difficulty_override": 15
})

result = response.json()
print(result["narration"])  # "The player hurls a blazing fireball at the goblin..."
```

## Testing Strategy

### Unit Tests
Each component can be tested independently:

```python
def test_fallback_parser():
    parser = FallbackParser()
    result = parser.parse_action("attack goblin with sword")
    assert result.action_type == ActionType.ATTACK
    assert result.weapon == "sword"

def test_game_engine_with_mocks():
    parser = MockParser()
    narrator = MockNarrator()
    engine = GameEngine(parser, narrator)
    # Test game logic without AI models
```

### Integration Tests
Test component interactions:

```python
def test_full_pipeline():
    engine = GameEngine(CodeLlamaParser(), PygmalionNarrator())
    request = NaturalLanguageRequest(player_input="cast fireball")
    result = engine.process_natural_language_action(request)
    assert "fireball" in result.narration.lower()
```

## Migration from Old Code

Your existing components can be gradually migrated:

1. **Keep old endpoints** for backwards compatibility
2. **Wrap existing classes** to implement new interfaces
3. **Add new endpoints** using the new architecture
4. **Migrate clients** to new endpoints over time

Example wrapper for your existing parser:

```python
class LegacyParserWrapper(ActionParser):
    def __init__(self):
        self.legacy_parser = CodeLlamaActionParser()  # Your existing class
    
    def load_model(self) -> bool:
        return self.legacy_parser.load_model()
    
    def parse_action(self, user_input: str, context: str = "") -> ParsedAction:
        result = self.legacy_parser.parse_action(user_input)
        # Convert to new ParsedAction format
        return ParsedAction(**result)
```

## Benefits for Expansion

This architecture makes it easy to:

- **Add new parsers** (e.g., GPT-4 based, fine-tuned models)
- **Add new narrators** (different AI models, different styles)
- **Add new game systems** (Pathfinder, Call of Cthulhu, etc.)
- **Add new interfaces** (Discord bot, web UI, etc.)
- **Add new features** (persistent character state, campaign tracking, etc.)

Each new component just needs to implement the appropriate interface and can be plugged into the existing system without changing core logic.

## Configuration

Environment variables and config files can easily be added:

```python
# config.py
CODELLAMA_PATH = os.getenv("CODELLAMA_PATH", "/default/path")
PYGMALION_PATH = os.getenv("PYGMALION_PATH", "/default/path")
DEFAULT_DIFFICULTY = int(os.getenv("DEFAULT_DIFFICULTY", "12"))

# main.py
server = create_server(
    parser_model_path=CODELLAMA_PATH,
    narrator_model_path=PYGMALION_PATH
)
```

This refactored architecture provides a solid foundation for expanding your D&D narrator system while maintaining clean separation of concerns and testability.