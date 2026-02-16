# neg-env — Multi-Agent Negotiation Environment

A research framework for running multi-agent negotiation and strategy games via a **Python API**. Run batch experiments with pluggable agents from a script — no server needed.

Python 3.10+.

## Install

```bash
pip install -e .
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

## Available games

| Game | ID | Description |
|------|----|-------------|
| Unfair Split | `unfair-split` | Two agents negotiate how to split a resource. Private reservation values. |
| First-Price Auction | `first-price-auction` | Two bidders submit sealed bids. Highest bid wins, pays own bid. |

## Documentation

Full documentation: **[marcellopoliti.github.io/agents-environment](https://marcellopoliti.github.io/agents-environment)**

- [Getting started](https://marcellopoliti.github.io/agents-environment/getting-started/quickstart/)
- [Games](https://marcellopoliti.github.io/agents-environment/games/overview/)
- [Writing custom agents](https://marcellopoliti.github.io/agents-environment/agents/custom-agents/)
- [LLM agents](https://marcellopoliti.github.io/agents-environment/agents/llm-agents/)
- [Experiment runner & results](https://marcellopoliti.github.io/agents-environment/experiments/runner/)
- [Type reference](https://marcellopoliti.github.io/agents-environment/reference/types/)

## Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
