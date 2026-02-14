# neg-env — Multi-Agent Negotiation Environment

A research framework for running multi-agent negotiation and strategy games via a **Python API**. Run batch experiments with pluggable agents from a script — no server needed.

Python 3.10+.

## Install

```bash
pip install -e .
```

## Quick start

Run 100 matches of unfair-split between two random agents:

```python
from neg_env import RandomAgent, ExperimentRunner, ExperimentConfig

config = ExperimentConfig(game_id="unfair-split", num_matches=100)
agents = [RandomAgent(agent_id="alice", seed=42), RandomAgent(agent_id="bob", seed=43)]
result = ExperimentRunner(config).run(agents)

print(f"Completion rate: {result.completion_rate:.0%}")
print(f"Mean payoffs: {result.mean_payoffs}")
```

## Available games

### Unfair split (`unfair-split`)

Two agents (proposer A, responder B) negotiate how to split resource R (default $100).

Each agent has a **private reservation value** v drawn uniformly from \[0, R/2\]. The reservation value represents the minimum amount needed for the deal to be worthwhile. Payoff on agreement: **u = x − v**, where x is the agent's share. If no agreement is reached within the round limit (default 10), both agents receive 0.

**Actions:**
- `submit_offer` — propose a split: `{"my_share": 60}` (0 to R)
- `accept` — accept the other agent's offer (ends the match)
- `reject` — reject and pass the turn for a counter-offer
- `pass` — hand the turn to the other agent (optionally send a message)
- `message_only` — send messages without advancing the turn

**Configuration:**
```python
from neg_env.games.fair_split import FairSplitGame
from neg_env.games import register_game

# Custom resource amount and round limit
game = FairSplitGame(total=200, max_rounds=20)
register_game(game)
```

## Writing a custom agent

Subclass `Agent` and implement two things: `agent_id` (property) and `act(state) -> AgentResponse`.

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
            their_share = offer  # what the offerer asked for themselves
            my_share = state.game_state["total"] - their_share
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

Then run it:

```python
from neg_env import ExperimentRunner, ExperimentConfig, RandomAgent

result = ExperimentRunner(ExperimentConfig(game_id="unfair-split", num_matches=50)).run(
    [FairAgent("fair"), RandomAgent(agent_id="random", seed=1)]
)
print(result.mean_payoffs)
```

### Agent interface

| Method | Required | Description |
|--------|----------|-------------|
| `agent_id` (property) | Yes | Unique string identifier |
| `act(state: TurnState) -> AgentResponse` | Yes | Observe game state, return messages + one game action |
| `on_match_start(match_id, game_id, agent_ids)` | No | Called before a match begins |
| `on_match_end(match_id, outcome)` | No | Called after a match ends |

### Turn model

Each turn, the current agent receives a `TurnState` and returns an `AgentResponse`:

- **Messages** (`AgentResponse.messages`) are delivered first. They do **not** consume a turn. You can send zero or more messages per turn (capped by `max_messages_per_turn`).
- **Action** (`AgentResponse.action`) is the game action (e.g. `submit_offer`, `accept`, `reject`). This advances the turn.

### Key types

**`TurnState`** — what your agent sees each turn:
- `match_id`, `game_id`, `agent_id` — identifiers
- `phase` — current game phase name
- `is_my_turn` — whether you can act
- `game_state` — game-specific dict (e.g. `{"total": 100, "current_offer": 60, "last_offer_by": "alice", "my_reservation_value": 12.5}`)
- `messages` — chat history visible to this agent
- `allowed_actions` — list of `AllowedAction` (action_type + payload_schema)
- `game_over`, `outcome` — set when the match ends

**`AgentResponse`** — what your agent returns:
- `messages: list[MessageIntent]` — optional messages (public or private)
- `action: Action` — the game action (`action_type` + `payload` dict)

**`ActionResult`** — returned by the environment after each action:
- `ok: bool` — whether the action was accepted
- `error: str | None` — error code (e.g. `"not_your_turn"`, `"invalid_payload"`, `"game_rule_violation"`)
- `error_detail: str | None` — human-readable explanation

## Experiment runner

`ExperimentRunner` runs N matches and collects structured results.

### Configuration

```python
from pathlib import Path
from neg_env import ExperimentConfig

config = ExperimentConfig(
    game_id="unfair-split",        # which game to play
    num_matches=100,               # how many matches to run
    max_turns_per_match=200,       # abort match after this many turns (default: 200)
    max_messages_per_turn=10,      # cap messages per agent per turn (default: 10)
    log_directory=Path("./logs"),   # save JSON logs per match (optional)
    metadata={"experiment": "baseline"},  # arbitrary metadata attached to logs
)
```

### Results

```python
result = ExperimentRunner(config).run(agents)

# Aggregate stats
result.completion_rate     # fraction of matches that finished (0.0 to 1.0)
result.mean_payoffs        # {"alice": 52.3, "bob": 47.7}
result.payoff_matrix       # {"alice": [60, 50, ...], "bob": [40, 50, ...]}
result.total_duration_seconds

# Per-match details
for mr in result.match_results:
    mr.match_id
    mr.outcome        # {"payoffs": [...], "reason": "agreement"}
    mr.status         # "finished" or "running" (if aborted by max_turns)
    mr.num_turns
    mr.num_messages
    mr.duration_seconds
    mr.log            # MatchLog object (full event trace)
    mr.error          # exception string if the match errored
```

### Match logs

When `log_directory` is set, each match writes a `{match_id}.json` file containing every event (actions, messages, errors, outcomes). Load them back for analysis:

```python
from neg_env.logging import MatchLogger

log = MatchLogger.load(Path("./logs/abc123.json"))
for event in log.events:
    print(event.event_type, event.agent_id, event.data)
```

## Built-in agents

| Agent | Description |
|-------|-------------|
| `RandomAgent(agent_id, seed)` | Picks a random allowed action. For tests and quick runs. |
| `LangChainNegotiationAgent(agent_id, system_prompt=..., provider=..., model=...)` | Game-agnostic LLM agent. You supply `system_prompt` (rules, actions, output format) for the game; the agent gets state and allowed actions from the runner. Supports `provider="openai"` or `"openrouter"`; keys from `.env` (`OPENAI_API_KEY`, `OPENROUTER_API_KEY`). Install: `pip install neg-env[langchain]`. |

## Dashboard

When running experiments, set `open_dashboard=True` in `ExperimentConfig` to open a live browser dashboard showing match progress and results in real time.

## Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Project layout

```
src/neg_env/
  __init__.py          Public API exports
  types.py             Core types (Action, TurnState, ActionResult, AgentResponse, ...)
  spec/                Game spec schema (GameSpec, Phase, TurnOrder, ...)
  core/                Match runner and match state
  games/               Game implementations (unfair-split) + registry
  agents/              Agent base class + RandomAgent + LangChainNegotiationAgent
  logging/             Match event logger (JSON logs)
  experiment/          ExperimentRunner for batch experiments
  prompts/             System prompts for LLM agents
```
