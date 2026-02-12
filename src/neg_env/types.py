"""Shared types for the negotiation environment."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageScope(str, Enum):
    """Who can see the message."""

    PUBLIC = "public"
    PRIVATE = "private"


class Message(BaseModel):
    """A message sent by an agent (public or private)."""

    message_id: str = Field(..., description="Unique id for this message")
    sender_id: str = Field(..., description="Agent who sent the message")
    scope: MessageScope = Field(..., description="Public or private")
    content: str = Field(..., description="Message text")
    to_agent_ids: list[str] = Field(default_factory=list, description="For private: recipient agent ids")
    timestamp_ns: int | None = Field(default=None, description="Optional monotonic timestamp")


class Action(BaseModel):
    """A single action (message or game action) performed by an agent."""

    action_type: str = Field(..., description="e.g. send_public_message, submit_offer, place_bid, accept")
    payload: dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")


class AllowedAction(BaseModel):
    """Describes an action the agent is allowed to take this turn."""

    action_type: str = Field(..., description="Type of action")
    description: str = Field(default="", description="Human-readable description")
    payload_schema: dict[str, Any] = Field(default_factory=dict, description="JSON schema for payload (optional)")


class TurnState(BaseModel):
    """What get_turn_state returns: everything the agent needs to decide and act."""

    match_id: str = Field(..., description="Current match id")
    game_id: str = Field(..., description="Game being played")
    agent_id: str = Field(..., description="Id of the agent receiving this state")
    phase: str = Field(..., description="Current phase name")
    is_my_turn: bool = Field(..., description="Whether this agent may act now")
    current_turn_agent_id: str | None = Field(default=None, description="Whose turn it is (if turn-based)")
    game_state: dict[str, Any] = Field(default_factory=dict, description="Visible game state (spec-defined)")
    messages: list[Message] = Field(default_factory=list, description="Recent messages this agent can see")
    allowed_actions: list[AllowedAction] = Field(default_factory=list, description="Actions allowed this turn")
    game_over: bool = Field(default=False, description="True if match has ended")
    outcome: dict[str, Any] | None = Field(default=None, description="If game_over: outcome and payoffs (spec-defined)")


class Payoff(BaseModel):
    """Payoff for one agent after the game ends."""

    agent_id: str = Field(..., description="Agent id")
    value: float = Field(..., description="Payoff value (e.g. dollars, utility)")
