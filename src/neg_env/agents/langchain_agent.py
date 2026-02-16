"""Game-agnostic LLM agent. Uses system_prompt (researcher-defined) and TurnState. Supports OpenAI and OpenRouter. Install: pip install neg-env[langchain]."""

import json
import os
import re
from typing import Any, Literal

from neg_env.agents.base import Agent
from neg_env.types import Action, AgentResponse, MessageIntent, MessageScope, TurnState


def _format_action_history(history: list[dict]) -> str:
    """Format action_history entries grouped by round into a readable summary."""
    if not history:
        return ""
    rounds: dict[int, list[str]] = {}
    for entry in history:
        r = entry.get("round", 0)
        agent = entry.get("agent_id", "?")
        action = entry.get("action", "?")
        if action == "submit_offer":
            desc = f"{agent} submitted offer (my_share={entry.get('my_share')})"
        elif action == "accept":
            desc = f"{agent} accepted"
        elif action == "reject":
            desc = f"{agent} rejected"
        elif action == "submit_bid":
            desc = f"{agent} submitted a sealed bid"
        elif action == "message_only":
            desc = f"{agent} [chat-only, no turn advance]"
        else:
            desc = f"{agent} {action}"
        rounds.setdefault(r, []).append(desc)
    lines = []
    for r in sorted(rounds):
        lines.append(f"  Round {r}: " + " → ".join(rounds[r]))
    return "negotiation_history:\n" + "\n".join(lines)


def _state_to_user_content(state: TurnState) -> str:
    """Serialize turn state for any game: game_state, messages, allowed_actions."""
    lines = [
        f"game_id={state.game_id} phase={state.phase} agent_id={state.agent_id}",
        f"game_state: {json.dumps(state.game_state)}",
    ]
    action_history = state.game_state.get("action_history") if isinstance(state.game_state, dict) else None
    if action_history:
        lines.append(_format_action_history(action_history))
    if state.messages:
        msg_lines = [f"{'you' if m.sender_id == state.agent_id else m.sender_id}: {m.content}" for m in state.messages]
        lines.append("messages:\n" + "\n".join(msg_lines))
    actions_desc = [f"{a.action_type}" + (f" ({a.description})" if a.description else "") for a in state.allowed_actions]
    lines.append("allowed_actions: " + ", ".join(actions_desc))
    lines.append('Reply with JSON only: {"message": "optional text or empty string", "action": "<action_type>", "payload": {...}}')
    return "\n".join(lines)


def _parse_llm_response(text: str) -> dict[str, Any]:
    m = re.search(r"\{[\s\S]*\}", text.strip())
    if not m:
        return {"message": "", "action": "", "payload": {}}
    try:
        d = json.loads(m.group())
        payload = dict(d.get("payload") or {})
        if "my_share" in d:
            payload["my_share"] = d["my_share"]
        return {"message": d.get("message", "") or "", "action": d.get("action", "") or "", "payload": payload}
    except json.JSONDecodeError:
        return {"message": "", "action": "", "payload": {}}


def _to_response(state: TurnState, parsed: dict[str, Any]) -> AgentResponse:
    allowed = {a.action_type for a in state.allowed_actions}
    action_type = (parsed.get("action") or "").strip()
    if action_type not in allowed:
        action_type = next(iter(allowed), "noop")
    msg = (parsed.get("message") or "").strip()
    return AgentResponse(
        messages=[MessageIntent(scope=MessageScope.PUBLIC, content=msg)] if msg else [],
        action=Action(action_type=action_type, payload=parsed.get("payload") or {}),
    )


def _fallback_action(state: TurnState) -> Action:
    a = next(iter(state.allowed_actions), None)
    return Action(action_type=a.action_type, payload={}) if a else Action(action_type="noop", payload={})


def _make_chain(provider: Literal["openai", "openrouter"], model: str, temperature: float, api_key: str | None):
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.runnables import RunnableLambda
    from langchain_openai import ChatOpenAI

    key = (api_key or os.environ.get("OPENROUTER_API_KEY") if provider == "openrouter" else api_key or os.environ.get("OPENAI_API_KEY"))
    llm = ChatOpenAI(model=model, temperature=temperature, api_key=key, base_url="https://openrouter.ai/api/v1" if provider == "openrouter" else None)
    def run(inp: dict[str, str]) -> str:
        out = llm.invoke([SystemMessage(content=inp["system"]), HumanMessage(content=inp["user"])])
        return out.content if hasattr(out, "content") else str(out)
    return RunnableLambda(run)


# Default prompt: researcher should override with game-specific prompt
DEFAULT_SYSTEM_PROMPT = """You are an agent in a multi-agent game. You receive the current game state, message history, and allowed actions. Respond with valid JSON only: {"message": "optional short message to others", "action": "<one of the allowed action types>", "payload": {}}."""


class LangChainNegotiationAgent(Agent):
    """Game-agnostic LLM agent. Researcher provides system_prompt for the game; keys from .env."""

    def __init__(
        self,
        agent_id: str = "llm",
        *,
        system_prompt: str | None = None,
        runnable: Any = None,
        provider: Literal["openai", "openrouter"] = "openai",
        model: str | None = None,
        temperature: float = 0.4,
        api_key: str | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._system_prompt = system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT
        self._runnable = runnable
        self._provider = provider
        self._model = model or ("gpt-4o-mini" if provider == "openai" else "openai/gpt-4o-mini")
        self._temperature = temperature
        self._api_key = api_key

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def act(self, state: TurnState) -> AgentResponse:
        if not state.allowed_actions:
            return AgentResponse(action=Action(action_type="noop", payload={}))
        user = _state_to_user_content(state)
        try:
            chain = self._runnable or _make_chain(self._provider, self._model, self._temperature, self._api_key)
            out = chain.invoke({"system": self._system_prompt, "user": user})
            text = out if isinstance(out, str) else getattr(out, "content", str(out))
            return _to_response(state, _parse_llm_response(text))
        except Exception as e:
            return AgentResponse(
                messages=[MessageIntent(scope=MessageScope.PUBLIC, content=f"(Error: {e})")],
                action=_fallback_action(state),
            )
