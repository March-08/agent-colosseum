# neg-env

A research framework for running multi-agent negotiation and strategy games via a **Python API**. Run batch experiments with pluggable agents from a script — no server needed.

## Features

- **Pluggable games** — built-in unfair split and first-price auction, or write your own
- **Pluggable agents** — from simple heuristics to LLM-powered agents (OpenAI, OpenRouter)
- **Batch experiments** — run N matches, collect structured results
- **Live dashboard** — browser-based real-time match viewer
- **JSON logging** — full event traces for every match

## Quick example

```python
from neg_env import RandomAgent, ExperimentRunner, ExperimentConfig

config = ExperimentConfig(game_id="unfair-split", num_matches=100)
agents = [RandomAgent(agent_id="alice", seed=42), RandomAgent(agent_id="bob", seed=43)]
result = ExperimentRunner(config).run(agents)

print(f"Deals: {result.num_matches - result.no_deal_count}/{result.num_matches}")
print(f"Mean utility: {result.mean_payoffs}")
```

## Next steps

- [Installation](getting-started/installation.md)
- [Quick Start](getting-started/quickstart.md)
- [Available games](games/overview.md)
- [Writing custom agents](agents/custom-agents.md)
