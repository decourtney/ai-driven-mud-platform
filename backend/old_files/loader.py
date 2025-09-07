from backend.game.game_registry import GAME_REGISTRY

def create_game_engine(game_slug, **kwargs):
    if game_slug not in GAME_REGISTRY:
        raise ValueError(f"Unknown game: {game_slug}")
    engine_cls = GAME_REGISTRY[game_slug]["engine"]
    return engine_cls(**kwargs)
