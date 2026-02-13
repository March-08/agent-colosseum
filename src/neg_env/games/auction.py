"""Simple auction: N agents discuss then place sealed bids."""

from neg_env.core.match import Match
from neg_env.spec import ActionTypeDef, GameSpec, OutcomeRule, Phase, TurnOrder
from neg_env.types import Action, ActionResult

from neg_env.games.base import Game


class SimpleAuctionGame(Game):
    """N agents; phase 1 free discussion, phase 2 sealed bid; highest wins."""

    def spec(self) -> GameSpec:
        return GameSpec(
            game_id="auction",
            name="Simple Auction",
            description="Agents may discuss, then each submits one sealed bid. Highest bid wins.",
            phases=[
                Phase(
                    name="discuss",
                    turn_order=TurnOrder.FREE,
                    allowed_action_types=["send_public_message", "send_private_message"],
                    duration_seconds=60.0,
                    max_actions_per_turn=10,
                ),
                Phase(
                    name="bidding",
                    turn_order=TurnOrder.SIMULTANEOUS,
                    allowed_action_types=["place_bid"],
                    max_rounds=1,
                    max_actions_per_turn=1,
                ),
            ],
            action_types=[
                ActionTypeDef(name="place_bid", description="Submit your bid (amount)", payload_schema={"amount": {"type": "number"}}, is_message=False),
            ],
            outcome_rule=OutcomeRule.ENGINE,
            initial_game_state={"bids": {}, "winner": None},
            allow_public_messages=True,
            allow_private_messages=True,
        )

    def compute_turn_state(self, match, agent_id):
        raise NotImplementedError("SimpleAuctionGame.compute_turn_state")

    def apply_action(self, match: Match, agent_id: str, action: Action) -> ActionResult:
        raise NotImplementedError("SimpleAuctionGame.apply_action")

    def compute_outcome(self, match):
        raise NotImplementedError("SimpleAuctionGame.compute_outcome")
