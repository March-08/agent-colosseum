"""Match runner: advances turns, applies actions, computes outcomes."""

import copy
import time
import uuid

from neg_env.spec import GameSpec
from neg_env.spec.schema import TurnOrder
from neg_env.types import Action, Message, MessageScope, TurnState

from neg_env.core.match import Match, MatchStatus


def create_match(match_id: str, game_id: str, spec: GameSpec, agent_ids: list[str]) -> Match:
    """Create a new match (waiting or running depending on spec)."""
    game_state = copy.deepcopy(spec.initial_game_state)
    status = MatchStatus.RUNNING
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


def apply_message(match: Match, sender_id: str, scope: str, content: str, to_agent_ids: list[str] | None) -> None:
    """Record a public or private message and advance state if needed."""
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
    if match.status != MatchStatus.RUNNING:
        return
    if not match.spec.phases:
        return
    phase = match.spec.phases[match.current_phase_index]
    if phase.turn_order != TurnOrder.ROUND_ROBIN or phase.max_actions_per_turn < 1:
        return
    n = len(match.agent_ids)
    if n == 0:
        return
    match.current_turn_index = (match.current_turn_index + 1) % n
    if match.current_turn_index == 0:
        match.current_round += 1


def apply_action(match: Match, agent_id: str, action: Action) -> None:
    """Apply a game action (e.g. submit_offer, place_bid); may advance turn/phase and set outcome."""
    from neg_env.games import get_game

    game = get_game(match.game_id)
    if game is None:
        return
    game.apply_action(match, agent_id, action)
    if match.status == MatchStatus.FINISHED:
        return
    outcome = game.compute_outcome(match)
    if outcome is not None:
        match.outcome = outcome
        match.status = MatchStatus.FINISHED


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
