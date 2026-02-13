"""Fair-split game: two agents negotiate how to split 100; alternating offers."""

from neg_env.core.match import Match, MatchStatus
from neg_env.spec import ActionTypeDef, GameSpec, OutcomeRule, Phase, TurnOrder
from neg_env.types import (
    Action,
    ActionError,
    ActionResult,
    AllowedAction,
    MessageScope,
    TurnState,
    action_error,
    action_ok,
)

from neg_env.games.base import Game


def _messages_visible_to(messages: list, agent_id: str) -> list:
    """Return messages this agent can see (public + private to/from them)."""
    out = []
    for m in messages:
        if m.scope == MessageScope.PUBLIC:
            out.append(m)
        elif agent_id == m.sender_id or agent_id in m.to_agent_ids:
            out.append(m)
    return out


def _build_allowed_actions(spec: GameSpec, phase_name: str, is_my_turn: bool) -> list[AllowedAction]:
    """Build allowed_actions from spec for current phase; only game actions (no message types)."""
    phase = next((p for p in spec.phases if p.name == phase_name), None)
    if phase is None or not is_my_turn:
        return []
    action_type_names = {
        at.name: at for at in spec.action_types if at.name in phase.allowed_action_types and not at.is_message
    }
    return [
        AllowedAction(action_type=name, description=at.description, payload_schema=at.payload_schema)
        for name, at in action_type_names.items()
    ]


class FairSplitGame(Game):
    """Two agents split $100; alternating offers, accept/reject."""

    def spec(self) -> GameSpec:
        return GameSpec(
            game_id="fair-split",
            name="Fair split",
            min_agents=2,
            description="Two agents must agree on how to split $100. Alternating offers; accept or counter.",
            phases=[
                Phase(
                    name="negotiation",
                    turn_order=TurnOrder.ROUND_ROBIN,
                    allowed_action_types=["send_public_message", "send_private_message", "submit_offer", "accept", "reject"],
                    max_rounds=10,
                    max_actions_per_turn=1,
                ),
            ],
            action_types=[
                ActionTypeDef(name="submit_offer", description="Propose a split (e.g. my_share)", payload_schema={"my_share": {"type": "number"}}, is_message=False),
                ActionTypeDef(name="accept", description="Accept current offer", payload_schema={}, is_message=False),
                ActionTypeDef(name="reject", description="Reject current offer", payload_schema={}, is_message=False),
            ],
            outcome_rule=OutcomeRule.AGREEMENT,
            initial_game_state={"total": 100, "current_offer": None, "last_offer_by": None},
            allow_public_messages=True,
            allow_private_messages=True,
        )

    def compute_turn_state(self, match: Match, agent_id: str) -> TurnState | None:
        if match.game_id != "fair-split":
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
                game_state=dict(match.game_state),
                messages=_messages_visible_to(match.messages, agent_id),
                allowed_actions=[],
                game_over=(match.status == MatchStatus.FINISHED),
                outcome=match.outcome,
            )
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
        last_offer_by = match.game_state.get("last_offer_by")
        if last_offer_by == agent_id:
            allowed_actions = [a for a in allowed_actions if a.action_type != "accept"]
        return TurnState(
            match_id=match.match_id,
            game_id=match.game_id,
            agent_id=agent_id,
            phase=phase_name,
            is_my_turn=is_my_turn,
            current_turn_agent_id=current_turn_agent_id,
            game_state=dict(match.game_state),
            messages=messages,
            allowed_actions=allowed_actions,
            game_over=(match.status == MatchStatus.FINISHED),
            outcome=match.outcome,
        )

    def _advance_turn_and_check_rounds(self, match: Match) -> None:
        n = len(match.agent_ids)
        if n == 0:
            return
        match.current_turn_index = (match.current_turn_index + 1) % n
        if match.current_turn_index == 0:
            match.current_round += 1
        phase = match.spec.phases[match.current_phase_index] if match.spec.phases else None
        if phase and phase.max_rounds is not None and match.current_round >= phase.max_rounds:
            total = match.game_state.get("total", 100)
            match.outcome = {
                "payoffs": [{"agent_id": aid, "value": 0.0} for aid in match.agent_ids],
                "reason": "max_rounds_exceeded",
                "total": total,
            }
            match.status = MatchStatus.FINISHED

    def apply_action(self, match: Match, agent_id: str, action: Action) -> ActionResult:
        if match.game_id != "fair-split":
            return action_error(ActionError.MATCH_NOT_RUNNING, "Not a fair-split match")
        if match.status != MatchStatus.RUNNING:
            return action_error(ActionError.MATCH_NOT_RUNNING, "Match is not running")
        phase = match.spec.phases[match.current_phase_index] if match.spec.phases else None
        if not phase or phase.name != "negotiation":
            return action_error(ActionError.MATCH_NOT_RUNNING, "Not in negotiation phase")
        n = len(match.agent_ids)
        if n == 0:
            return action_error(ActionError.MATCH_NOT_RUNNING, "No agents in match")
        current_turn_agent_id = match.agent_ids[match.current_turn_index]
        if agent_id != current_turn_agent_id:
            return action_error(ActionError.NOT_YOUR_TURN, f"It is {current_turn_agent_id}'s turn")
        total = match.game_state.get("total", 100)

        if action.action_type == "submit_offer":
            my_share = action.payload.get("my_share")
            if my_share is None:
                return action_error(ActionError.INVALID_PAYLOAD, "my_share is required")
            try:
                my_share = float(my_share)
            except (TypeError, ValueError):
                return action_error(ActionError.INVALID_PAYLOAD, "my_share must be a number")
            if not (0 <= my_share <= total):
                return action_error(ActionError.INVALID_PAYLOAD, f"my_share must be between 0 and {total}")
            match.game_state["current_offer"] = my_share
            match.game_state["last_offer_by"] = agent_id
            self._advance_turn_and_check_rounds(match)
            return action_ok()

        if action.action_type == "accept":
            current_offer = match.game_state.get("current_offer")
            last_offer_by = match.game_state.get("last_offer_by")
            if current_offer is None or last_offer_by is None:
                return action_error(ActionError.GAME_RULE_VIOLATION, "No active offer to accept")
            if last_offer_by == agent_id:
                return action_error(ActionError.GAME_RULE_VIOLATION, "Cannot accept your own offer")
            payoffs = []
            for aid in match.agent_ids:
                if aid == last_offer_by:
                    payoffs.append({"agent_id": aid, "value": float(current_offer)})
                else:
                    payoffs.append({"agent_id": aid, "value": float(total - current_offer)})
            match.outcome = {"payoffs": payoffs, "reason": "agreement"}
            match.status = MatchStatus.FINISHED
            return action_ok()

        if action.action_type == "reject":
            self._advance_turn_and_check_rounds(match)
            return action_ok()

        return action_error(ActionError.INVALID_ACTION_TYPE, f"Unknown action type: {action.action_type}")

    def compute_outcome(self, match: Match) -> dict | None:
        if match.status == MatchStatus.FINISHED and match.outcome is not None:
            return match.outcome
        return None
