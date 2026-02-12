"""Split $100: two agents negotiate how to split 100; alternating offers."""

from neg_env.spec import ActionTypeDef, GameSpec, OutcomeRule, Phase, TurnOrder

from neg_env.games.base import Game


class Split100Game(Game):
    """Two agents split $100; alternating offers, accept/reject."""

    def spec(self) -> GameSpec:
        return GameSpec(
            game_id="split100",
            name="Split $100",
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

    def compute_turn_state(self, match, agent_id):
        raise NotImplementedError("Split100Game.compute_turn_state")

    def apply_action(self, match, agent_id, action):
        raise NotImplementedError("Split100Game.apply_action")

    def compute_outcome(self, match):
        raise NotImplementedError("Split100Game.compute_outcome")
