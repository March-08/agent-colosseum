# First-Price Sealed-Bid Auction

**Game ID:** `first-price-auction`

Two bidders each have a private valuation for an item. They can chat before bidding, then submit sealed bids. Highest bid wins and pays own bid.

## Rules

- Each bidder has a **private valuation** drawn uniformly from [0, 100].
- Bidders can chat via `message_only` before committing to a bid.
- Each bidder submits exactly **one sealed bid** (irreversible).
- Bids are sealed: you can see whether the opponent has bid, but **not their bid amount**.
- **Highest bid wins.** Winner pays their own bid. Ties broken randomly.
- **Utility:** winner = `valuation - bid`, loser = `0`.
- If the round limit is reached without both bids submitted, both get utility 0.

## Actions

| Action | Payload | Description |
|--------|---------|-------------|
| `submit_bid` | `{"bid": 40}` | Submit a sealed bid. Must be >= 0. Once submitted, cannot be changed. One bid per agent. |
| `pass` | `{}` | Hand the turn to the other agent. Advances round count. |
| `message_only` | `{}` | Send messages without advancing the turn. |

## Visible game state

Each agent sees:

```python
{
    "my_valuation": 60.0,        # your private valuation (opponent cannot see)
    "my_bid": 40.0,              # your bid (or None if not yet submitted)
    "opponent_has_bid": True,    # whether opponent has bid (not the amount)
    "action_history": [...]      # tracks submit_bid (no amounts) and message_only
}
```

!!! warning "Sealed bids"
    The `action_history` records `submit_bid` entries **without the bid amount**. Agents only learn bid values after the match ends (in the outcome).

## Configuration

```python
from neg_env import FirstPriceAuctionGame

# Defaults
game = FirstPriceAuctionGame()  # max_rounds=10, random valuations

# Custom
game = FirstPriceAuctionGame(max_rounds=25)

# Fixed valuations (for controlled experiments)
game = FirstPriceAuctionGame(
    max_rounds=25,
    valuations={"bidder_a": 60, "bidder_b": 80},
)
```

## Outcome format

```python
{
    "payoffs": [
        {"agent_id": "bidder_a", "bid": 40, "utility": 20.0},  # winner: 60 - 40
        {"agent_id": "bidder_b", "bid": 35, "utility": 0.0},   # loser
    ],
    "reason": "auction_resolved",    # or "max_rounds_exceeded"
    "winner": "bidder_a",
}
```

## Dashboard metrics

The dashboard and console output show auction-specific metrics:

- **Resolved / Timed out** — how many auctions completed vs expired
- **Mean bids** — average bid per agent (resolved matches only)
- **Mean utility (valuation - bid)** — average utility per agent (resolved matches only)

## Prompts

One built-in system prompt for LLM agents:

```python
from neg_env.prompts import SYSTEM_PROMPT_AUCTION
```

The prompt instructs the agent to chat before bidding, avoid revealing its valuation, and bid below valuation to ensure positive utility.

## Example

```python
from pathlib import Path
from dotenv import load_dotenv
from neg_env import ExperimentConfig, ExperimentRunner, LangChainNegotiationAgent
from neg_env.prompts import SYSTEM_PROMPT_AUCTION
from neg_env.games.first_price_auction import FirstPriceAuctionGame

load_dotenv()

agents = [
    LangChainNegotiationAgent(
        agent_id="bidder_a", provider="openai",
        model="gpt-4o-mini", system_prompt=SYSTEM_PROMPT_AUCTION,
    ),
    LangChainNegotiationAgent(
        agent_id="bidder_b", provider="openai",
        model="gpt-4o-mini", system_prompt=SYSTEM_PROMPT_AUCTION,
    ),
]

game = FirstPriceAuctionGame(max_rounds=25, valuations={"bidder_a": 60, "bidder_b": 80})
config = ExperimentConfig(
    game_id="first-price-auction", num_matches=5,
    log_directory=Path("./logs/auction"), open_dashboard=True,
)
result = ExperimentRunner(config).run(agents, game=game)
```
