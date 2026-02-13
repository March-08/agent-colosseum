"""Agent base class: abstract interface for programmatic agents."""

from abc import ABC, abstractmethod
from typing import Any

from neg_env.types import AgentResponse, TurnState


class Agent(ABC):
    """Base class for agents that play negotiation games."""

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Unique identifier for this agent."""
        ...

    @abstractmethod
    def act(self, state: TurnState) -> AgentResponse:
        """Given the current turn state, return messages + a game action."""
        ...

    def on_match_start(self, match_id: str, game_id: str, agent_ids: list[str]) -> None:
        """Called when a match begins. Override for setup logic."""

    def on_match_end(self, match_id: str, outcome: dict[str, Any] | None) -> None:
        """Called when a match ends. Override for teardown/logging."""
