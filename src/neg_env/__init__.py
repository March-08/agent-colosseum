"""Negotiation environment: MCP server for multi-agent bargaining and strategy games."""

__version__ = "0.1.0"

# Core types
from neg_env.types import Action, ActionResult, AgentResponse, MessageIntent, TurnState

# Agent abstractions
from neg_env.agents import Agent, RandomAgent

# Experiment runner
from neg_env.experiment import ExperimentConfig, ExperimentResult, ExperimentRunner

# Game registry
from neg_env.games import get_game_spec, list_game_ids, register_game

__all__ = [
    # Types
    "Action",
    "ActionResult",
    "AgentResponse",
    "MessageIntent",
    "TurnState",
    # Agents
    "Agent",
    "RandomAgent",
    # Experiment
    "ExperimentConfig",
    "ExperimentResult",
    "ExperimentRunner",
    # Registry
    "get_game_spec",
    "list_game_ids",
    "register_game",
]
