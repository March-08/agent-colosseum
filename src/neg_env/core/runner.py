"""Match runner: advances turns, applies actions, computes outcomes."""

from neg_env.spec import GameSpec
from neg_env.types import Action, Message, TurnState

from neg_env.core.match import Match, MatchStatus


def create_match(match_id: str, game_id: str, spec: GameSpec, agent_ids: list[str]) -> Match:
    """Create a new match (waiting or running depending on spec)."""
    # Stub: no logic yet
    raise NotImplementedError("create_match: implement with spec.initial_game_state and status=RUNNING when enough agents")


def get_turn_state(match: Match, agent_id: str) -> TurnState | None:
    """Return the turn state for the given agent (what they see and can do)."""
    # Stub: no logic yet
    raise NotImplementedError("get_turn_state: implement from match.game_state, messages, phase, allowed_actions")


def apply_message(match: Match, sender_id: str, scope: str, content: str, to_agent_ids: list[str] | None) -> None:
    """Record a public or private message and advance state if needed."""
    # Stub: no logic yet
    raise NotImplementedError("apply_message: append message, possibly advance turn/round/phase")


def apply_action(match: Match, agent_id: str, action: Action) -> None:
    """Apply a game action (e.g. submit_offer, place_bid); may advance turn/phase and set outcome."""
    # Stub: no logic yet
    raise NotImplementedError("apply_action: validate, update game_state, advance turn/phase, compute outcome when done")


class MatchRunner:
    """Facade for match lifecycle and actions (optional; can use module-level functions)."""

    def __init__(self) -> None:
        self._matches: dict[str, Match] = {}

    def create_match(self, match_id: str, game_id: str, spec: GameSpec, agent_ids: list[str]) -> Match:
        """Create and store a new match."""
        match = create_match(match_id, game_id, spec, agent_ids)
        self._matches[match_id] = match
        return match

    def get_match(self, match_id: str) -> Match | None:
        """Return match by id."""
        return self._matches.get(match_id)

    def get_turn_state(self, match_id: str, agent_id: str) -> TurnState | None:
        """Return turn state for agent in this match."""
        match = self._matches.get(match_id)
        if match is None:
            return None
        return get_turn_state(match, agent_id)

    def send_public_message(self, match_id: str, sender_id: str, content: str) -> bool:
        """Record a public message; return True if accepted."""
        match = self._matches.get(match_id)
        if match is None:
            return False
        apply_message(match, sender_id, "public", content, None)
        return True

    def send_private_message(
        self, match_id: str, sender_id: str, content: str, to_agent_ids: list[str]
    ) -> bool:
        """Record a private message; return True if accepted."""
        match = self._matches.get(match_id)
        if match is None:
            return False
        apply_message(match, sender_id, "private", content, to_agent_ids)
        return True

    def perform_action(self, match_id: str, agent_id: str, action_type: str, payload: dict) -> bool:
        """Apply a game action; return True if accepted."""
        match = self._matches.get(match_id)
        if match is None:
            return False
        from neg_env.types import Action

        apply_action(match, agent_id, Action(action_type=action_type, payload=payload))
        return True
