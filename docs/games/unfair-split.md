# Unfair Split

**Game ID:** `unfair-split`

Two agents (proposer A, responder B) negotiate how to split a resource R (default $100).

## Rules

- Each agent has a **private reservation value** `v` drawn uniformly from [0, R/2].
- Agents take turns making offers, accepting, or rejecting.
- **Payoff on agreement:** `u = x - v`, where `x` is the agent's share.
- If no agreement is reached within the round limit, both get utility 0.

## Actions

| Action | Payload | Description |
|--------|---------|-------------|
| `submit_offer` | `{"my_share": 60}` | Propose a split: you get `my_share`, they get `total - my_share`. Must be between 0 and total. |
| `accept` | `{}` | Accept the other agent's offer (ends the match). Cannot accept your own offer. |
| `reject` | `{}` | Reject the current offer and pass the turn. |
| `pass` | `{}` | Hand the turn to the other agent. |
| `message_only` | `{}` | Send messages without advancing the turn. |

## Visible game state

Each agent sees:

```python
{
    "total": 100,
    "current_offer": 60,          # current offer on the table (or None)
    "last_offer_by": "alice",     # who made the current offer
    "my_reservation_value": 12.5, # your private value (opponent cannot see this)
    "action_history": [...]       # full history of offers, accepts, rejects
}
```

## Configuration

```python
from neg_env import FairSplitGame

# Defaults
game = FairSplitGame()  # total=100, max_rounds=10

# Custom
game = FairSplitGame(total=200, max_rounds=20)

# Fixed reservation values (for controlled experiments)
game = FairSplitGame(
    total=100,
    reservation_values={"alice": 10, "bob": 30},
)
```

## Outcome format

```python
{
    "payoffs": [
        {"agent_id": "alice", "share": 60, "utility": 47.5},
        {"agent_id": "bob", "share": 40, "utility": 27.5},
    ],
    "reason": "agreement",        # or "max_rounds_exceeded"
    "split": [60, 40],
}
```

## Prompts

Two built-in system prompts for LLM agents:

- `SYSTEM_PROMPT_FAIR` — cooperative: aims for a fair split, prefers deals over deadlock.
- `SYSTEM_PROMPT_UNFAIR` — strategic: maximizes payoff, uses anchoring, calibrated concessions, deadline pressure.

```python
from neg_env.prompts import SYSTEM_PROMPT_FAIR, SYSTEM_PROMPT_UNFAIR
```
