"""Shared response parsing and state→user content for LLM-based negotiation agents."""

import json
import re
from typing import Any

from neg_env.prompts.fair_split import SYSTEM_PROMPT_FAIR, SYSTEM_PROMPT_UNFAIR
from neg_env.types import Action, AgentResponse, MessageIntent, MessageScope, TurnState

__all__ = [
    "fallback_action",
    "parsed_to_agent_response",
    "parse_llm_response",
    "state_to_user_content",
]


def state_to_user_content(state: TurnState) -> str:
    total = state.game_state.get("total", 100)
    current_offer = state.game_state.get("current_offer")
    last_offer_by = state.game_state.get("last_offer_by")
    from_messages = []
    for m in state.messages:
        role = "other" if m.sender_id != state.agent_id else "you"
        from_messages.append(f"{role}: {m.content}")
    msg_history = "\n".join(from_messages) if from_messages else "(no messages yet)"
    lines = [
        f"You are agent '{state.agent_id}'. Total to split: ${total}.",
        f"Current offer on table: {current_offer if current_offer is not None else 'None'} (by {last_offer_by or 'nobody'}).",
        f"Message history:\n{msg_history}",
        "Allowed actions this turn: " + ", ".join(a.action_type for a in state.allowed_actions) + ".",
        "Reply with JSON only: {\"message\": \"...\", \"action\": \"...\", \"my_share\": ...}",
    ]
    return "\n".join(lines)


def parse_llm_response(text: str) -> dict[str, Any]:
    text = text.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group())
    return {"message": "", "action": "reject", "my_share": None}


def fallback_action(state: TurnState) -> Action:
    for a in state.allowed_actions:
        if a.action_type == "submit_offer":
            return Action(action_type="submit_offer", payload={"my_share": 50.0})
        if a.action_type == "reject":
            return Action(action_type="reject", payload={})
        if a.action_type == "accept":
            return Action(action_type="accept", payload={})
    return Action(action_type="noop", payload={})


def parsed_to_agent_response(state: TurnState, parsed: dict[str, Any]) -> AgentResponse:
    allowed_types = {a.action_type for a in state.allowed_actions}
    msg_content = (parsed.get("message") or "").strip() or "I'd like to find a fair split."
    action_type = parsed.get("action") or "reject"
    my_share = parsed.get("my_share")
    if action_type not in allowed_types:
        action_type = "reject" if "reject" in allowed_types else next(iter(allowed_types))
    if action_type == "submit_offer":
        try:
            my_share = float(my_share) if my_share is not None else 50.0
        except (TypeError, ValueError):
            my_share = 50.0
        my_share = max(0, min(state.game_state.get("total", 100), my_share))
        action = Action(action_type="submit_offer", payload={"my_share": round(my_share, 2)})
    elif action_type == "accept":
        action = Action(action_type="accept", payload={})
    else:
        action = Action(action_type="reject", payload={})
    return AgentResponse(
        messages=[MessageIntent(scope=MessageScope.PUBLIC, content=msg_content)],
        action=action,
    )
