# Quick Start

## Run a batch of matches

```python
from neg_env import RandomAgent, ExperimentRunner, ExperimentConfig

config = ExperimentConfig(game_id="unfair-split", num_matches=100)
agents = [RandomAgent(agent_id="alice", seed=42), RandomAgent(agent_id="bob", seed=43)]
result = ExperimentRunner(config).run(agents)

print(f"Deals: {result.num_matches - result.no_deal_count}/{result.num_matches}")
print(f"Mean shares (deal): {result.mean_shares}")
print(f"Mean utility: {result.mean_payoffs}")
```

## Use LLM agents

```python
from dotenv import load_dotenv
from neg_env import LangChainNegotiationAgent, ExperimentRunner, ExperimentConfig
from neg_env.prompts import SYSTEM_PROMPT_UNFAIR

load_dotenv()  # loads OPENAI_API_KEY from .env

agents = [
    LangChainNegotiationAgent(
        agent_id="agent_a",
        provider="openai",
        model="gpt-4o-mini",
        system_prompt=SYSTEM_PROMPT_UNFAIR,
    ),
    LangChainNegotiationAgent(
        agent_id="agent_b",
        provider="openai",
        model="gpt-4o-mini",
        system_prompt=SYSTEM_PROMPT_UNFAIR,
    ),
]

config = ExperimentConfig(game_id="unfair-split", num_matches=5, open_dashboard=True)
result = ExperimentRunner(config).run(agents)
```

## Custom game settings

```python
from neg_env import FairSplitGame

game = FairSplitGame(total=200, max_rounds=20)
result = ExperimentRunner(config).run(agents, game=game)

# Pin reservation values for controlled experiments
game = FairSplitGame(total=100, reservation_values={"agent_a": 10, "agent_b": 30})
result = ExperimentRunner(config).run(agents, game=game)
```
