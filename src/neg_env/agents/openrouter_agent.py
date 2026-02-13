"""LLM-backed negotiation agent using OpenRouter (GPT). Negotiates via messages before acting."""

import json
import os
from typing import Any

import httpx

from neg_env.agents.base import Agent
from neg_env.agents.negotiation_llm import (
    fallback_action,
    parsed_to_agent_response,
    parse_llm_response,
    state_to_user_content,
)
from neg_env.prompts.fair_split import SYSTEM_PROMPT_FAIR as DEFAULT_SYSTEM_PROMPT
from neg_env.types import Action, AgentResponse, MessageIntent, MessageScope, TurnState

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"


class OpenRouterNegotiationAgent(Agent):
    """Agent that uses OpenRouter (e.g. GPT) to negotiate: sends a message then chooses an action."""

    def __init__(
        self,
        agent_id: str = "llm",
        *,
        system_prompt: str | None = None,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.4,
        timeout: float = 30.0,
    ) -> None:
        self._agent_id = agent_id
        self._system_prompt = system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT
        self._api_key = (api_key or os.environ.get("OPENROUTER_API_KEY")) or ""
        self._model = model
        self._temperature = temperature
        self._timeout = timeout

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def act(self, state: TurnState) -> AgentResponse:
        if not state.allowed_actions:
            return AgentResponse(action=Action(action_type="noop", payload={}))

        user_content = state_to_user_content(state)
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_content},
        ]
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": 512,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(OPENROUTER_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            return AgentResponse(
                messages=[MessageIntent(scope=MessageScope.PUBLIC, content=f"(API error: {e})")],
                action=fallback_action(state),
            )

        choice = (data.get("choices") or [None])[0]
        if not choice:
            return AgentResponse(action=fallback_action(state))
        content = (choice.get("message") or {}).get("content") or ""
        parsed = parse_llm_response(content)
        return parsed_to_agent_response(state, parsed)
