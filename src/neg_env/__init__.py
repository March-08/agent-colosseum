"""Negotiation environment: framework for multi-agent bargaining and strategy games."""

__version__ = "0.1.0"

# Core types
from neg_env.types import Action, ActionResult, AgentResponse, MessageIntent, TurnState

# Agent abstractions
from neg_env.agents import Agent, RandomAgent
try:
    from neg_env.agents import LangChainNegotiationAgent  # noqa: F401
except ImportError:

    class LangChainNegotiationAgent:  # type: ignore[no-redef]
        """Placeholder that raises a helpful error when langchain extras are missing."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "LangChainNegotiationAgent requires the langchain extra. "
                "Install it with: pip install -e '.[langchain]'"
            )

# Experiment runner
from neg_env.experiment import ExperimentConfig, ExperimentResult, ExperimentRunner

# Game registry
from neg_env.games import get_game_spec, list_game_ids, register_game

# Built-in games
from neg_env.games.fair_split import FairSplitGame
from neg_env.games.first_price_auction import FirstPriceAuctionGame

__all__ = [
    # Types
    "Action",
    "ActionResult",
    "AgentResponse",
    "MessageIntent",
    "TurnState",
    # Agents
    "Agent",
    "LangChainNegotiationAgent",
    "RandomAgent",
    # Experiment
    "ExperimentConfig",
    "ExperimentResult",
    "ExperimentRunner",
    # Registry
    "get_game_spec",
    "list_game_ids",
    "register_game",
    # Games
    "FairSplitGame",
    "FirstPriceAuctionGame",
]
