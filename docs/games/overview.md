# Games

neg-env ships with two built-in games. Each game defines its own rules, actions, and outcome computation.

| Game | ID | Description |
|------|----|-------------|
| [Unfair Split](unfair-split.md) | `unfair-split` | Two agents negotiate how to split a resource. Private reservation values. |
| [First-Price Auction](first-price-auction.md) | `first-price-auction` | Two bidders submit sealed bids. Highest bid wins, pays own bid. |

## Common patterns

All games share:

- **Round-robin turns** — agents alternate. On your turn you pick one action.
- **`message_only`** — send chat messages without advancing the turn. Agents can have multi-turn conversations before committing to a game action.
- **`pass`** — skip your turn (hand it to the other agent).
- **`action_history`** — a list in `game_state` tracking every game action taken, visible to both agents. Agents can inspect it to reason about what happened.
- **Private information** — each agent has private values (reservation value or valuation) that the opponent cannot see.
- **Max rounds** — if the game isn't resolved within the round limit, both agents get utility 0.

## Game state

Each turn, your agent receives a `TurnState` with a `game_state` dict. This dict is game-specific and filtered per agent — you only see what the game allows you to see.
