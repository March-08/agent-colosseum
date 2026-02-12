"""Game implementations: each game provides a spec and (later) step/outcome logic."""

from neg_env.games.base import Game
from neg_env.games.registry import get_game, get_game_spec, list_game_ids, register_game

__all__ = ["Game", "get_game", "get_game_spec", "list_game_ids", "register_game"]
