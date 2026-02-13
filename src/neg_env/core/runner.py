"""Match runner: advances turns, applies actions, computes outcomes."""

import copy
import time
import uuid
from collections import deque

from neg_env.spec import GameSpec
from neg_env.spec.schema import TurnOrder
from neg_env.types import (
    Action,
    ActionError,
    ActionResult,
    Message,
    MessageScope,
    TurnState,
    action_error,
    action_ok,
)

from neg_env.core.match import Match, MatchStatus


def create_match(match_id: str, game_id: str, spec: GameSpec, agent_ids: list[str]) -> Match:
    """Create a new match (WAITING until min_agents have joined, then RUNNING)."""
    game_state = copy.deepcopy(spec.initial_game_state)
    min_agents = getattr(spec, "min_agents", 1)
    status = MatchStatus.RUNNING if len(agent_ids) >= min_agents else MatchStatus.WAITING
    return Match(
        match_id=match_id,
        game_id=game_id,
        spec=spec,
        agent_ids=list(agent_ids),
        status=status,
        current_phase_index=0,
        current_round=0,
        current_turn_index=0,
        game_state=game_state,
        messages=[],
        outcome=None,
    )


def _build_placeholder_turn_state(match: Match, agent_id: str) -> TurnState:
    """Build a minimal TurnState from match when the game does not implement compute_turn_state yet."""
    phase = match.spec.phases[match.current_phase_index].name if match.spec.phases else ""
    current_turn_agent_id: str | None = None
    is_my_turn = False
    if match.agent_ids and 0 <= match.current_turn_index < len(match.agent_ids):
        current_turn_agent_id = match.agent_ids[match.current_turn_index]
        is_my_turn = current_turn_agent_id == agent_id
    return TurnState(
        match_id=match.match_id,
        game_id=match.game_id,
        agent_id=agent_id,
        phase=phase,
        is_my_turn=is_my_turn,
        current_turn_agent_id=current_turn_agent_id,
        game_state=dict(match.game_state),
        messages=list(match.messages),
        allowed_actions=[],
        game_over=(match.status == MatchStatus.FINISHED),
        outcome=match.outcome,
    )


def get_turn_state(match: Match, agent_id: str) -> TurnState | None:
    """Return the turn state for the given agent (what they see and can do)."""
    from neg_env.games import get_game

    game = get_game(match.game_id)
    if game is None:
        return _build_placeholder_turn_state(match, agent_id)
    try:
        return game.compute_turn_state(match, agent_id)
    except NotImplementedError:
        return _build_placeholder_turn_state(match, agent_id)


def apply_message(match: Match, sender_id: str, scope: str, content: str, to_agent_ids: list[str] | None) -> ActionResult:
    """Record a public or private message. Messages do NOT advance turns."""
    if match.status != MatchStatus.RUNNING:
        return action_error(ActionError.MATCH_NOT_RUNNING, "Match is not running")
    if sender_id not in match.agent_ids:
        return action_error(ActionError.AGENT_NOT_IN_MATCH, f"Agent {sender_id} is not in this match")
    scope_enum = MessageScope.PUBLIC if scope == "public" else MessageScope.PRIVATE
    to_list = list(to_agent_ids) if to_agent_ids else []
    msg = Message(
        message_id=uuid.uuid4().hex,
        sender_id=sender_id,
        scope=scope_enum,
        content=content,
        to_agent_ids=to_list,
        timestamp_ns=time.time_ns(),
    )
    match.messages.append(msg)
    return action_ok()


def apply_action(match: Match, agent_id: str, action: Action) -> ActionResult:
    """Apply a game action (e.g. submit_offer, accept); may advance turn/phase and set outcome."""
    from neg_env.games import get_game

    game = get_game(match.game_id)
    if game is None:
        return action_error(ActionError.MATCH_NOT_FOUND, f"No game registered for {match.game_id}")
    result = game.apply_action(match, agent_id, action)
    if not result.ok:
        return result
    if match.status == MatchStatus.FINISHED:
        return result
    outcome = game.compute_outcome(match)
    if outcome is not None:
        match.outcome = outcome
        match.status = MatchStatus.FINISHED
    return result


MAX_EVENTS_PER_MATCH = 500


class MatchRunner:
    """Facade for match lifecycle and actions (optional; can use module-level functions)."""

    def __init__(self) -> None:
        self._matches: dict[str, Match] = {}
        self._match_events: dict[str, deque] = {}

    def create_match(self, match_id: str, game_id: str, spec: GameSpec, agent_ids: list[str]) -> Match:
        """Create and store a new match."""
        match = create_match(match_id, game_id, spec, agent_ids)
        self._matches[match_id] = match
        self._match_events[match_id] = deque(maxlen=MAX_EVENTS_PER_MATCH)
        return match

    def record_match_event(self, match_id: str, event: str, **kwargs: object) -> None:
        """Append an event to the match's history (for dashboard)."""
        if match_id not in self._matches:
            return
        if match_id not in self._match_events:
            self._match_events[match_id] = deque(maxlen=MAX_EVENTS_PER_MATCH)
        self._match_events[match_id].append({
            "event": event,
            "timestamp": round(time.time(), 3),
            **kwargs,
        })

    def get_match_events(self, match_id: str) -> list[dict]:
        """Return event history for a match (newest last)."""
        return list(self._match_events.get(match_id, []))

    def get_match(self, match_id: str) -> Match | None:
        """Return match by id."""
        return self._matches.get(match_id)

    def get_turn_state(self, match_id: str, agent_id: str) -> TurnState | None:
        """Return turn state for agent in this match."""
        match = self._matches.get(match_id)
        if match is None:
            return None
        return get_turn_state(match, agent_id)

    def send_public_message(self, match_id: str, sender_id: str, content: str) -> ActionResult:
        """Record a public message; return ActionResult."""
        match = self._matches.get(match_id)
        if match is None:
            return action_error(ActionError.MATCH_NOT_FOUND, "Match not found")
        return apply_message(match, sender_id, "public", content, None)

    def send_private_message(
        self, match_id: str, sender_id: str, content: str, to_agent_ids: list[str]
    ) -> ActionResult:
        """Record a private message; return ActionResult."""
        match = self._matches.get(match_id)
        if match is None:
            return action_error(ActionError.MATCH_NOT_FOUND, "Match not found")
        return apply_message(match, sender_id, "private", content, to_agent_ids)

    def perform_action(self, match_id: str, agent_id: str, action_type: str, payload: dict) -> ActionResult:
        """Apply a game action; return ActionResult."""
        match = self._matches.get(match_id)
        if match is None:
            return action_error(ActionError.MATCH_NOT_FOUND, "Match not found")
        return apply_action(match, agent_id, Action(action_type=action_type, payload=payload))
