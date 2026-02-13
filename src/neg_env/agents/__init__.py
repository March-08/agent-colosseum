"""Agent abstractions: base class and built-in agents."""

from neg_env.agents.base import Agent
from neg_env.agents.framework_base import LLMNegotiationBase
from neg_env.agents.openrouter_agent import OpenRouterNegotiationAgent
from neg_env.agents.random_agent import RandomAgent

__all__ = ["Agent", "LLMNegotiationBase", "OpenRouterNegotiationAgent", "RandomAgent"]

try:
    from neg_env.agents.langchain_agent import LangChainNegotiationAgent
    __all__ = [*__all__, "LangChainNegotiationAgent"]
except ImportError:
    LangChainNegotiationAgent = None  # type: ignore[misc, assignment]
