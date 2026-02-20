# Experiment Runner

`ExperimentRunner` runs N matches with pluggable agents and collects structured results.

## Configuration

```python
from pathlib import Path
from neg_env import ExperimentConfig

config = ExperimentConfig(
    game_id="unfair-split",          # which game to play
    num_matches=100,                 # how many matches to run
    max_turns_per_match=200,         # abort match after this many turns
    max_messages_per_turn=10,        # cap messages per agent per turn
    max_message_pings=5,             # max reply rounds for message_only exchanges
    log_directory=Path("./logs"),    # save JSON logs per match (optional)
    metadata={"experiment": "v1"},   # arbitrary metadata attached to logs
    open_dashboard=True,             # open live browser dashboard
    dashboard_port=8765,             # port for dashboard server
    max_workers=4,                   # run matches in parallel (default: 1)
    opik_enabled=True,               # enable Opik experiment tracing
    opik_project_name="my-project",  # Opik project name
)
```

## Parallel execution

Set `max_workers` to run multiple matches concurrently using a thread pool. This is especially useful for LLM-backed agents where most time is spent waiting on API calls.

```python
config = ExperimentConfig(
    game_id="unfair-split",
    num_matches=50,
    max_workers=8,   # 8 matches run in parallel
)
```

## Opik tracing

When `opik_enabled=True`, each experiment run is logged to [Opik](https://www.comet.com/site/products/opik/) for analysis and comparison. Set `OPIK_API_KEY` and `OPIK_WORKSPACE` in your environment (see `.env.example`).

```python
config = ExperimentConfig(
    game_id="unfair-split",
    num_matches=10,
    opik_enabled=True,
    opik_project_name="unfair-split-v2",
)
```

## Running

```python
from neg_env import ExperimentRunner, RandomAgent

agents = [RandomAgent(agent_id="alice", seed=42), RandomAgent(agent_id="bob", seed=43)]
result = ExperimentRunner(config).run(agents)

# Or with custom game settings
from neg_env import FairSplitGame
result = ExperimentRunner(config).run(agents, game=FairSplitGame(total=200))
```

## Results

`ExperimentResult` provides aggregate statistics and per-match details.

### Aggregate stats

```python
result.no_deal_count         # matches without resolution
result.mean_payoffs          # {"alice": 42.3, "bob": 32.7} — mean utility
result.payoff_matrix         # {"alice": [60, 50, ...], "bob": [...]} — all payoffs
result.completion_rate       # fraction of matches that finished (0.0–1.0)
result.total_duration_seconds
```

**For unfair-split:**

```python
result.mean_shares           # {"alice": 55.0, "bob": 45.0} — mean deal amounts
```

**For first-price-auction:**

```python
result.mean_bids             # {"bidder_a": 38.5, "bidder_b": 42.0} — mean bids
```

### Per-match details

```python
for mr in result.match_results:
    mr.match_id
    mr.outcome          # game-specific outcome dict
    mr.status           # "finished" or "running" (if aborted)
    mr.num_turns
    mr.num_messages
    mr.duration_seconds
    mr.log              # MatchLog object (full event trace)
    mr.error            # exception string if the match errored
```
