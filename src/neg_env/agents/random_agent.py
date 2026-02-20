"""RandomAgent: picks a random allowed action with valid random payload."""

import random
import threading
import uuid

from neg_env.agents.base import Agent
from neg_env.types import Action, AgentResponse, TurnState


class RandomAgent(Agent):
    """Agent that picks a random allowed action with a valid random payload."""

    def __init__(self, agent_id: str | None = None, seed: int | None = None) -> None:
        self._agent_id = agent_id or f"random_{uuid.uuid4().hex[:8]}"
        self._rng = random.Random(seed)
        self._rng_lock = threading.Lock()

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def act(self, state: TurnState) -> AgentResponse:
        if not state.allowed_actions:
            return AgentResponse(action=Action(action_type="noop", payload={}))
        with self._rng_lock:
            chosen = self._rng.choice(state.allowed_actions)
            payload = self._random_payload(chosen.action_type)
        return AgentResponse(action=Action(action_type=chosen.action_type, payload=payload))

    def _random_payload(self, action_type: str) -> dict:
        """Generate a valid random payload for known action types.

        Must be called while holding self._rng_lock.
        """
        if action_type == "submit_offer":
            return {"my_share": round(self._rng.uniform(0, 100), 2)}
        if action_type in ("accept", "reject", "pass", "message_only", "noop"):
            return {}
        return {}
