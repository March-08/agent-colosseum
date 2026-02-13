# neg-env — Multi-Agent Negotiation Environment

A framework for running multi-agent negotiation and strategy games. Use it two ways:

- **Python API** — run batch experiments with pluggable agents from a script. No server needed.
- **MCP server** — connect AI clients (Cursor, Claude Desktop) for live interactive play.

Python 3.10+.

## Install

```bash
pip install -e .
```

## Quick start (Python API)

Run 100 matches of Split $100 between two random agents in four lines:

```python
from neg_env import RandomAgent, ExperimentRunner, ExperimentConfig

config = ExperimentConfig(game_id="split100", num_matches=100)
agents = [RandomAgent(agent_id="alice", seed=42), RandomAgent(agent_id="bob", seed=43)]
result = ExperimentRunner(config).run(agents)

print(f"Completion rate: {result.completion_rate:.0%}")
print(f"Mean payoffs: {result.mean_payoffs}")
```

## Writing a custom agent

Subclass `Agent` and implement two things: `agent_id` (property) and `act(state) -> AgentResponse`.

```python
from neg_env import Agent, Action, AgentResponse, TurnState, MessageIntent
from neg_env.types import MessageScope

class FairSplitAgent(Agent):
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

result = ExperimentRunner(ExperimentConfig(game_id="split100", num_matches=50)).run(
    [FairSplitAgent("fair"), RandomAgent(agent_id="random", seed=1)]
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
- `game_state` — game-specific dict (e.g. `{"total": 100, "current_offer": 60, "last_offer_by": "alice"}`)
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
    game_id="split100",          # which game to play
    num_matches=100,             # how many matches to run
    max_turns_per_match=200,     # abort match after this many turns (default: 200)
    max_messages_per_turn=10,    # cap messages per agent per turn (default: 10)
    log_directory=Path("./logs"),  # save JSON logs per match (optional)
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
| `RandomAgent(agent_id, seed)` | Picks a random allowed action with a valid random payload. Seeded for reproducibility. |

## Available games

### Split $100 (`split100`)

Two agents negotiate how to split $100 via alternating offers.

**Actions:**
- `submit_offer` — propose a split: `{"my_share": 60}` (0-100)
- `accept` — accept the other agent's offer (ends the match)
- `reject` — reject and pass the turn for a counter-offer

**Outcome:** on agreement, payoffs reflect the accepted offer. If max rounds (10) are exceeded, both agents get 0.

### Simple Auction (`auction`)

N-agent sealed-bid auction (stub — spec defined, logic not yet implemented).

## MCP server (interactive play)

For live play with AI clients, run the MCP server. This is a separate interface from the Python API.

### One server, many clients

You run **one** neg-env server. **Multiple MCP clients** connect to create matches, join games, and play. The server holds all match state.

- **SSE (default)**: listens on `http://127.0.0.1:8000`. All clients connect to that URL. One process, shared matches.
- **stdio**: the client spawns the server as a subprocess. One process per client.

### Run the server

```bash
# SSE (recommended for multi-agent play)
python -m neg_env
# Or: python -m neg_env --transport sse --host 127.0.0.1 --port 8000

# stdio (for single-client tools like Cursor)
python -m neg_env --transport stdio
```

### Connect Cursor (SSE)

1. Start the server in a terminal (leave it running).
2. In Cursor: **Settings > Features > MCP** (or **Settings > MCP**).
3. Click **Add new MCP server**.
4. Set **Type** to **SSE**, **Server URL** to `http://127.0.0.1:8000/sse`.

Or edit `mcp.json` directly:

```json
{
  "mcpServers": {
    "neg-env": {
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

### Connect Claude Desktop (SSE via mcp-remote)

Claude Desktop requires a command. Use the mcp-remote bridge to connect to the same SSE server:

```json
{
  "mcpServers": {
    "neg-env": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://127.0.0.1:8000/sse"]
    }
  }
}
```

Requires Node.js/npx. Cursor (direct SSE) and Claude (via mcp-remote) can share the same server and play the same match.

### Connect Cursor (stdio)

```json
{
  "mcpServers": {
    "neg-env": {
      "command": "python",
      "args": ["-m", "neg_env", "--transport", "stdio"]
    }
  }
}
```

### MCP tools

| Tool | Description |
|------|-------------|
| `list_games` | List available game ids |
| `get_game_rules` | Get spec for a game by id |
| `start_game` | Create a new match; returns match_id + agent_id |
| `join_game` | Join an existing match by invite code |
| `get_turn_state` | Get current state, messages, and allowed actions |
| `send_public_message` | Send a message visible to all agents |
| `send_private_message` | Send a message to specific agents |
| `perform_action` | Perform a game action (submit_offer, accept, etc.) |

## Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

| Test file | What it covers |
|-----------|---------------|
| `test_core.py` | Match runner, create_match, get_turn_state, apply_message |
| `test_game_split100.py` | Split100 game flow (offer, accept, reject, error codes) |
| `test_agents.py` | Agent base class, RandomAgent |
| `test_logging.py` | MatchLogger save/load, event logging |
| `test_experiment.py` | ExperimentRunner, batch matches, payoff stats |
| `test_server_mcp.py` | MCP tool definitions |

## Project layout

```
src/neg_env/
  __init__.py          Public API exports
  types.py             Core types (Action, TurnState, ActionResult, AgentResponse, ...)
  spec/                Game spec schema (GameSpec, Phase, TurnOrder, ...)
  core/                Match runner and match state
  games/               Game implementations (split100, auction) + registry
  agents/              Agent base class + RandomAgent
  logging/             Match event logger (JSON logs)
  experiment/          ExperimentRunner for batch experiments
  server/              MCP server and tool handlers
```
