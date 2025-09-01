from backend.game.dnd_engine.engine import DndEngine

GAME_REGISTRY = {
    "mudai": {
        "engine": DndEngine,
        "title": "MudAI",
        "description": "Embark on an epic text-based adventure powered by artificial intelligence. Every choice matters, every story is unique. Experience classic MUD gameplay enhanced with modern AI storytelling.",
        "playerCount": 0,
        "status": "active",
        "difficulty": "beginner",
        "estimatedTime": "30+ min",
        "features": [
            "AI-Powered Storytelling",
            "Dynamic World Events",
            "Character Progression",
            "Endless Possibilities"
        ],
        "thumbnail": "",
        "tags": ["featured", "fantasy", "text-based"]
    },
    "cyberquest": {
        "engine": DndEngine,  # Placeholder until a sci-fi engine exists
        "title": "CyberQuest",
        "description": "Hack, infiltrate, and survive in a neon-drenched cyberpunk city. Your choices determine the fate of factions, corporations, and yourself.",
        "playerCount": 0,
        "status": "active",
        "difficulty": "intermediate",
        "estimatedTime": "45+ min",
        "features": [
            "Branching Narrative",
            "Hacking Mini-Games",
            "Dynamic NPC Alliances",
            "Procedural City Events"
        ],
        "thumbnail": "",
        "tags": ["sci-fi", "cyberpunk", "text-based"]
    },
    "shadows_of_the_deep": {
        "engine": DndEngine,  # Placeholder until a horror engine exists
        "title": "Shadows of the Deep",
        "description": "Descend into the abyss and uncover horrors older than mankind. Survival depends on your wits and your sanity.",
        "playerCount": 0,
        "status": "active",
        "difficulty": "hard",
        "estimatedTime": "60+ min",
        "features": [
            "Sanity System",
            "Non-linear Exploration",
            "Multiple Endings",
            "Atmospheric Horror"
        ],
        "thumbnail": "",
        "tags": ["horror", "mystery", "text-based"]
    }
}
