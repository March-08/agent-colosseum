# Writing a Custom Agent

Subclass `Agent` and implement `agent_id` (property) and `act(state) -> AgentResponse`.

## Example: 50/50 agent

```python
from neg_env import Agent, Action, AgentResponse, TurnState, MessageIntent
from neg_env.types import MessageScope

class FairAgent(Agent):
    """Always proposes a 50/50 split; accepts any offer >= 40."""

    def __init__(self, name: str):
        self._name = name

    @property
    def agent_id(self) -> str:
        return self._name

    def act(self, state: TurnState) -> AgentResponse:
        offer = state.game_state.get("current_offer")
        last_by = state.game_state.get("last_offer_by")

        # If there's an offer from the other agent and it's fair enough, accept
        if offer is not None and last_by != self.agent_id:
            my_share = state.game_state["total"] - offer
            if my_share >= 40:
                return AgentResponse(
                    messages=[MessageIntent(scope=MessageScope.PUBLIC, content="Deal!")],
                    action=Action(action_type="accept", payload={}),
                )

        # Otherwise propose 50/50
        return AgentResponse(
            messages=[MessageIntent(scope=MessageScope.PUBLIC, content="I propose 50/50.")],
            action=Action(action_type="submit_offer", payload={"my_share": 50}),
        )
```

## Running it

```python
from neg_env import ExperimentRunner, ExperimentConfig, RandomAgent

result = ExperimentRunner(ExperimentConfig(game_id="unfair-split", num_matches=50)).run(
    [FairAgent("fair"), RandomAgent(agent_id="random", seed=1)]
)
print(result.mean_payoffs)
```

## What your agent receives

Each turn, `act()` receives a `TurnState`:

- `game_state` — game-specific dict with visible information (offers, valuations, history)
- `messages` — chat history visible to this agent
- `allowed_actions` — list of actions available this turn (with payload schemas)
- `is_my_turn` — whether you can act
- `game_over`, `outcome` — set when the match ends

## What your agent returns

`AgentResponse` contains:

- `messages: list[MessageIntent]` — optional messages (public or private). Delivered before the action.
- `action: Action` — one game action (`action_type` + `payload` dict). Must be one of the `allowed_actions`.

## Lifecycle hooks

Override these for setup/teardown:

```python
def on_match_start(self, match_id: str, game_id: str, agent_ids: list[str]) -> None:
    """Called before a match begins."""

def on_match_end(self, match_id: str, outcome: dict | None) -> None:
    """Called after a match ends. Inspect outcome for results."""
```
