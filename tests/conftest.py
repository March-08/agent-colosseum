"""Pytest fixtures: register games so get_game works in tests."""

import pytest

from neg_env.games import register_game
from neg_env.games.auction import SimpleAuctionGame
from neg_env.games.split100 import Split100Game


@pytest.fixture(scope="session", autouse=True)
def register_builtin_games():
    """Register split100 and auction so runner get_turn_state can resolve games."""
    register_game(Split100Game())
    register_game(SimpleAuctionGame())
