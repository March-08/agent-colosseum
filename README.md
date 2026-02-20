# neg-env — Multi-Agent Negotiation Environment

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A research framework for running multi-agent negotiation and strategy games via a **Python API**. Run batch experiments with pluggable agents from a script — no server needed.

Python 3.10+.

## Install

```bash
pip install -e .
```

With LLM agent support:

```bash
pip install -e ".[langchain]"
```

With [Opik](https://www.comet.com/site/products/opik/) tracing:

```bash
pip install -e ".[opik]"
```

## Quick start

```python
from neg_env import RandomAgent, ExperimentRunner, ExperimentConfig

config = ExperimentConfig(game_id="unfair-split", num_matches=100)
agents = [RandomAgent(agent_id="alice", seed=42), RandomAgent(agent_id="bob", seed=43)]
result = ExperimentRunner(config).run(agents)

print(f"Deals: {result.num_matches - result.no_deal_count}/{result.num_matches}")
print(f"Mean utility: {result.mean_payoffs}")
```

## Features

- **Pluggable agents** — built-in `RandomAgent`, LLM-backed `LangChainNegotiationAgent`, or write your own
- **Parallel execution** — run matches concurrently with `max_workers`
- **Live dashboard** — browser-based real-time experiment dashboard
- **Opik tracing** — optional experiment tracing via `opik_enabled=True`
- **Structured results** — aggregate stats, per-match details, and JSON logs

## Available games

| Game | ID | Description |
|------|----|-------------|
| Unfair Split | `unfair-split` | Two agents negotiate how to split a resource. Private reservation values. |
| First-Price Auction | `first-price-auction` | Two bidders submit sealed bids. Highest bid wins, pays own bid. |

## Examples

See [`examples/`](examples/) for ready-to-run scripts:

- [`unfair_split.py`](examples/unfair_split.py) — two LLM agents negotiate a resource split
- [`first_price_auction.py`](examples/first_price_auction.py) — two LLM bidders in a sealed-bid auction

## Documentation

Full documentation: **[site-seven-indol-67.vercel.app](https://site-seven-indol-67.vercel.app)**

- [Getting started](https://site-seven-indol-67.vercel.app/getting-started/quickstart/)
- [Games](https://site-seven-indol-67.vercel.app/games/overview/)
- [Writing custom agents](https://site-seven-indol-67.vercel.app/agents/custom-agents/)
- [LLM agents](https://site-seven-indol-67.vercel.app/agents/llm-agents/)
- [Experiment runner & results](https://site-seven-indol-67.vercel.app/experiments/runner/)
- [Type reference](https://site-seven-indol-67.vercel.app/reference/types/)

## Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
