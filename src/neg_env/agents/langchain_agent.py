"""LangChain-based negotiation agent. Install with: pip install neg-env[langchain]."""

from typing import Any

from neg_env.agents.base import Agent
from neg_env.agents.negotiation_llm import (
    fallback_action,
    parsed_to_agent_response,
    parse_llm_response,
    state_to_user_content,
)
from neg_env.prompts.fair_split import SYSTEM_PROMPT_FAIR
from neg_env.types import Action, AgentResponse, MessageIntent, MessageScope, TurnState


def _default_chain(model: str, temperature: float, api_key: str | None):
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnableLambda
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
    )

    def run(inp: dict[str, str]) -> str:
        out = llm.invoke(
            [SystemMessage(content=inp["system"]), HumanMessage(content=inp["user"])]
        )
        return out.content if hasattr(out, "content") else str(out)

    return RunnableLambda(run)


class LangChainNegotiationAgent(Agent):
    """Negotiation agent using a LangChain runnable. Uses default prompt+LLM chain if runnable not provided."""

    def __init__(
        self,
        agent_id: str = "langchain",
        *,
        system_prompt: str | None = None,
        runnable: Any = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.4,
        api_key: str | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._system_prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT_FAIR
        self._runnable = runnable
        self._model = model
        self._temperature = temperature
        self._api_key = api_key

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def _get_runnable(self):
        if self._runnable is not None:
            return self._runnable
        import os

        key = self._api_key or os.environ.get("OPENAI_API_KEY")
        return _default_chain(self._model, self._temperature, key)

    def act(self, state: TurnState) -> AgentResponse:
        if not state.allowed_actions:
            return AgentResponse(action=Action(action_type="noop", payload={}))

        user_content = state_to_user_content(state)
        inp = {"system": self._system_prompt, "user": user_content}

        try:
            runnable = self._get_runnable()
            out = runnable.invoke(inp)
            text = out if isinstance(out, str) else getattr(out, "content", str(out))
        except Exception as e:
            return AgentResponse(
                messages=[MessageIntent(scope=MessageScope.PUBLIC, content=f"(Error: {e})")],
                action=fallback_action(state),
            )

        parsed = parse_llm_response(text)
        return parsed_to_agent_response(state, parsed)
