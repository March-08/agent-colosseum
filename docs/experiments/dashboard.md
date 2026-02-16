# Dashboard

Set `open_dashboard=True` in `ExperimentConfig` to open a live browser dashboard during experiments.

## Enabling

```python
config = ExperimentConfig(
    game_id="unfair-split",
    num_matches=10,
    open_dashboard=True,
    dashboard_port=8765,     # default port
)
```

The dashboard opens automatically at `http://127.0.0.1:8765` and polls for updates every 800ms.

## What it shows

### Summary section

The dashboard adapts its metrics to the game being played:

**Unfair split:**

- **Deals / No-deal** — how many matches reached agreement
- **Mean shares** — average deal amount per agent (agreements only)
- **Mean utility (share - v)** — average utility per agent (agreements only)

**First-price auction:**

- **Resolved / Timed out** — how many auctions completed vs expired
- **Mean bids** — average bid per agent (resolved only)
- **Mean utility (valuation - bid)** — average utility per agent (resolved only)

### Match details

Click on any match to expand its event trace: every message, action, and outcome.

### Live match

While a match is running, the dashboard shows a live event stream for the current match.
