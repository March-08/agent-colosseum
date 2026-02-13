"""Base interface for games: spec + optional step/outcome logic."""

from typing import Any

from neg_env.spec import GameSpec

from neg_env.core.match import Match
from neg_env.types import Action, ActionResult, TurnState


class Game:
    """Abstract game: provides spec and (when implemented) transition and outcome logic."""

    def spec(self) -> GameSpec:
        """Return the game specification."""
        raise NotImplementedError

    def compute_turn_state(self, match: Match, agent_id: str) -> TurnState | None:
        """Build TurnState for this agent from current match state. None if not this game."""
        raise NotImplementedError("compute_turn_state: implement per game")

    def apply_action(self, match: Match, agent_id: str, action: Action) -> ActionResult:
        """Apply action; update match.game_state and match status/outcome. Return ActionResult."""
        raise NotImplementedError("apply_action: implement per game")

    def compute_outcome(self, match: Match) -> dict[str, Any] | None:
        """If game is over, return outcome dict (e.g. payoffs). Otherwise None."""
        raise NotImplementedError("compute_outcome: implement per game")
