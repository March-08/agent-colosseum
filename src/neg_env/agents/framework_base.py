"""Base for framework-backed LLM agents (LangChain, etc.)."""

from abc import ABC, abstractmethod

from neg_env.agents.base import Agent


class LLMNegotiationBase(Agent, ABC):
    """Base for agents that use an LLM to negotiate: you implement _invoke_llm(system, user) -> str."""

    @abstractmethod
    def _invoke_llm(self, system_prompt: str, user_content: str) -> str:
        """Call the LLM; return the raw response text (expected to contain JSON)."""
        ...
