# Match Logging

When `log_directory` is set in `ExperimentConfig`, each match writes a `{match_id}.json` file containing every event.

## Enabling

```python
from pathlib import Path

config = ExperimentConfig(
    game_id="unfair-split",
    num_matches=10,
    log_directory=Path("./logs"),
)
```

## Log format

Each JSON file contains:

```json
{
    "match_id": "abc123...",
    "game_id": "unfair-split",
    "agent_ids": ["alice", "bob"],
    "events": [
        {
            "event_type": "match_start",
            "timestamp_ns": 1234567890,
            "agent_id": null,
            "data": {}
        },
        {
            "event_type": "action",
            "agent_id": "alice",
            "data": {"action_type": "submit_offer", "payload": {"my_share": 60}, "ok": true}
        }
    ],
    "outcome": { ... },
    "metadata": { ... }
}
```

## Loading logs

```python
from pathlib import Path
from neg_env.logging import MatchLogger

log = MatchLogger.load(Path("./logs/abc123.json"))
for event in log.events:
    print(event.event_type, event.agent_id, event.data)
```
