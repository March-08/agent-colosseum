"""First-price sealed-bid auction: two bidders chat, then submit sealed bids. Highest bid wins, pays own bid."""

import random
from neg_env.core.match import Match, MatchStatus
from neg_env.spec import ActionTypeDef, GameSpec, OutcomeRule, Phase, TurnOrder
from neg_env.types import (
    Action,
    ActionError,
    ActionResult,
    TurnState,
    action_error,
    action_ok,
)

from neg_env.games.base import Game
from neg_env.games.utils import _messages_visible_to, _build_allowed_actions


GAME_ID = "first-price-auction"


class FirstPriceAuctionGame(Game):
    """First-price sealed-bid auction: two bidders each have a private valuation.

    They can chat via message_only, then submit sealed bids.
    Highest bid wins and pays own bid. Utility: winner = valuation - bid, loser = 0.
    If max_rounds exceeded without both bids, both get utility 0.
    """

    def __init__(self, *, max_rounds: int = 10, valuations: dict[str, float] | None = None) -> None:
        self._max_rounds = max_rounds
        self._fixed_valuations = valuations

    def spec(self) -> GameSpec:
        return GameSpec(
            game_id=GAME_ID,
            name="First-price sealed-bid auction",
            min_agents=2,
            description=(
                "Two bidders each have a private valuation drawn uniformly from [0, 100]. "
                "They can chat before bidding. Each submits one sealed bid (irreversible). "
                "Highest bid wins and pays own bid. "
                f"Utility: winner = valuation − bid, loser = 0. "
                f"If no bids within {self._max_rounds} rounds, both get 0."
            ),
            phases=[
                Phase(
                    name="auction",
                    turn_order=TurnOrder.ROUND_ROBIN,
                    allowed_action_types=["submit_bid", "pass", "message_only"],
                    max_rounds=self._max_rounds,
                ),
            ],
            action_types=[
                ActionTypeDef(
                    name="submit_bid",
                    description="Submit a sealed bid (irreversible, once per agent)",
                    payload_schema={"bid": {"type": "number"}},
                    is_message=False,
                ),
                ActionTypeDef(name="pass", description="Pass the turn to the other agent", payload_schema={}, is_message=False),
                ActionTypeDef(name="message_only", description="Only send messages; do not advance turn", payload_schema={}, is_message=False),
            ],
            outcome_rule=OutcomeRule.ENGINE,
            initial_game_state={
                "bids": {},
                "valuations": None,
                "action_history": [],
            },
        )

    def _ensure_valuations(self, match: Match) -> None:
        if match.game_state.get("valuations") is not None:
            return
        if self._fixed_valuations is not None:
            match.game_state["valuations"] = dict(self._fixed_valuations)
            return
        rng = random.Random(f"{match.match_id}")
        vals = [round(rng.uniform(0, 100), 2) for _ in match.agent_ids]
        match.game_state["valuations"] = dict(zip(match.agent_ids, vals))

    def _visible_game_state(self, match: Match, agent_id: str) -> dict:
        g = match.game_state
        valuations = g.get("valuations") or {}
        bids = g.get("bids") or {}
        opponent_ids = [aid for aid in match.agent_ids if aid != agent_id]
        out: dict = {}
        if agent_id in valuations:
            out["my_valuation"] = valuations[agent_id]
        out["my_bid"] = bids.get(agent_id)
        out["opponent_has_bid"] = any(oid in bids for oid in opponent_ids)
        out["action_history"] = g.get("action_history", [])
        return out

    def compute_turn_state(self, match: Match, agent_id: str) -> TurnState | None:
        if match.game_id != GAME_ID:
            return None
        if match.status != MatchStatus.RUNNING:
            phase_name = "waiting_for_players"
            only_agent = match.agent_ids[0] if match.agent_ids else None
            return TurnState(
                match_id=match.match_id,
                game_id=match.game_id,
                agent_id=agent_id,
                phase=phase_name,
                is_my_turn=False,
                current_turn_agent_id=only_agent,
                game_state={},
                messages=_messages_visible_to(match.messages, agent_id),
                allowed_actions=[],
                game_over=(match.status == MatchStatus.FINISHED),
                outcome=match.outcome,
            )
        self._ensure_valuations(match)
        phase = match.spec.phases[match.current_phase_index] if match.spec.phases else None
        phase_name = phase.name if phase else ""
        n = len(match.agent_ids)
        idx = match.current_turn_index
        if idx < 0 or idx >= n:
            idx = 0
        current_turn_agent_id = match.agent_ids[idx] if n else None
        is_my_turn = current_turn_agent_id == agent_id
        messages = _messages_visible_to(match.messages, agent_id)
        allowed_actions = _build_allowed_actions(match.spec, phase_name, is_my_turn)
        # If agent already submitted a bid, remove submit_bid from allowed actions
        bids = match.game_state.get("bids") or {}
        if agent_id in bids:
            allowed_actions = [a for a in allowed_actions if a.action_type != "submit_bid"]
        return TurnState(
            match_id=match.match_id,
            game_id=match.game_id,
            agent_id=agent_id,
            phase=phase_name,
            is_my_turn=is_my_turn,
            current_turn_agent_id=current_turn_agent_id,
            game_state=self._visible_game_state(match, agent_id),
            messages=messages,
            allowed_actions=allowed_actions,
            game_over=(match.status == MatchStatus.FINISHED),
            outcome=match.outcome,
        )

    def _advance_turn_only(self, match: Match) -> None:
        n = len(match.agent_ids)
        if n == 0:
            return
        match.current_turn_index = (match.current_turn_index + 1) % n

    def _advance_turn_and_check_rounds(self, match: Match) -> None:
        n = len(match.agent_ids)
        if n == 0:
            return
        match.current_turn_index = (match.current_turn_index + 1) % n
        if match.current_turn_index == 0:
            match.current_round += 1
        phase = match.spec.phases[match.current_phase_index] if match.spec.phases else None
        if phase and phase.max_rounds is not None and match.current_round >= phase.max_rounds:
            match.outcome = {
                "payoffs": [{"agent_id": aid, "utility": 0.0} for aid in match.agent_ids],
                "reason": "max_rounds_exceeded",
            }
            match.status = MatchStatus.FINISHED

    def _resolve_auction(self, match: Match) -> None:
        bids = match.game_state["bids"]
        valuations = match.game_state["valuations"]
        agents = list(bids.keys())
        bid_values = [(aid, bids[aid]) for aid in agents]
        max_bid = max(b for _, b in bid_values)
        top_bidders = [aid for aid, b in bid_values if b == max_bid]
        if len(top_bidders) == 1:
            winner = top_bidders[0]
        else:
            rng = random.Random(f"{match.match_id}_tiebreak")
            winner = rng.choice(top_bidders)
        payoffs = []
        for aid in match.agent_ids:
            bid = bids[aid]
            if aid == winner:
                utility = round(valuations[aid] - bid, 2)
            else:
                utility = 0.0
            payoffs.append({"agent_id": aid, "bid": bid, "utility": utility})
        match.outcome = {
            "payoffs": payoffs,
            "reason": "auction_resolved",
            "winner": winner,
        }
        match.status = MatchStatus.FINISHED

    def apply_action(self, match: Match, agent_id: str, action: Action) -> ActionResult:
        if match.game_id != GAME_ID:
            return action_error(ActionError.MATCH_NOT_RUNNING, "Not a first-price-auction match")
        if match.status != MatchStatus.RUNNING:
            return action_error(ActionError.MATCH_NOT_RUNNING, "Match is not running")
        phase = match.spec.phases[match.current_phase_index] if match.spec.phases else None
        if not phase or phase.name != "auction":
            return action_error(ActionError.MATCH_NOT_RUNNING, "Not in auction phase")
        n = len(match.agent_ids)
        if n == 0:
            return action_error(ActionError.MATCH_NOT_RUNNING, "No agents in match")
        current_turn_agent_id = match.agent_ids[match.current_turn_index]
        if agent_id != current_turn_agent_id:
            return action_error(ActionError.NOT_YOUR_TURN, f"It is {current_turn_agent_id}'s turn")

        if action.action_type == "submit_bid":
            bids = match.game_state.get("bids") or {}
            if agent_id in bids:
                return action_error(ActionError.GAME_RULE_VIOLATION, "You have already submitted a bid")
            bid = action.payload.get("bid")
            if bid is None:
                return action_error(ActionError.INVALID_PAYLOAD, "bid is required")
            try:
                bid = float(bid)
            except (TypeError, ValueError):
                return action_error(ActionError.INVALID_PAYLOAD, "bid must be a number")
            if bid < 0:
                return action_error(ActionError.INVALID_PAYLOAD, "bid must be >= 0")
            bids[agent_id] = bid
            match.game_state["bids"] = bids
            match.game_state.setdefault("action_history", []).append(
                {"agent_id": agent_id, "action": "submit_bid", "round": match.current_round}
            )
            # Check if all agents have bid
            if all(aid in bids for aid in match.agent_ids):
                self._resolve_auction(match)
                return action_ok()
            self._advance_turn_and_check_rounds(match)
            return action_ok()

        if action.action_type == "pass":
            self._advance_turn_and_check_rounds(match)
            return action_ok()

        if action.action_type == "message_only":
            match.game_state.setdefault("action_history", []).append(
                {"agent_id": agent_id, "action": "message_only", "round": match.current_round, "advances_turn": False}
            )
            return action_ok()

        return action_error(ActionError.INVALID_ACTION_TYPE, f"Unknown action type: {action.action_type}")

    def compute_outcome(self, match: Match) -> dict | None:
        if match.status == MatchStatus.FINISHED and match.outcome is not None:
            return match.outcome
        return None
