# Type Reference

## Core types

### `TurnState`

What your agent sees each turn.

| Field | Type | Description |
|-------|------|-------------|
| `match_id` | `str` | Match identifier |
| `game_id` | `str` | Game identifier |
| `agent_id` | `str` | Your agent's ID |
| `phase` | `str` | Current game phase name |
| `is_my_turn` | `bool` | Whether you can act |
| `current_turn_agent_id` | `str \| None` | Whose turn it is |
| `game_state` | `dict` | Game-specific visible state |
| `messages` | `list[Message]` | Chat history visible to you |
| `allowed_actions` | `list[AllowedAction]` | Available actions with payload schemas |
| `game_over` | `bool` | Whether the match has ended |
| `outcome` | `dict \| None` | Final outcome (set when game_over) |

### `AgentResponse`

What your agent returns.

| Field | Type | Description |
|-------|------|-------------|
| `messages` | `list[MessageIntent]` | Messages to send (delivered before action) |
| `action` | `Action` | Game action to take |

### `Action`

A game action.

| Field | Type | Description |
|-------|------|-------------|
| `action_type` | `str` | Action name (e.g. `"submit_offer"`, `"submit_bid"`) |
| `payload` | `dict` | Action-specific data |

### `ActionResult`

Returned by the environment after each action.

| Field | Type | Description |
|-------|------|-------------|
| `ok` | `bool` | Whether the action was accepted |
| `error` | `str \| None` | Error code (`"not_your_turn"`, `"invalid_payload"`, `"game_rule_violation"`) |
| `error_detail` | `str \| None` | Human-readable explanation |

### `MessageIntent`

A message to send.

| Field | Type | Description |
|-------|------|-------------|
| `scope` | `MessageScope` | `PUBLIC` or `PRIVATE` |
| `content` | `str` | Message text |
| `to_agent_ids` | `list[str] \| None` | Recipients (for private messages) |

### `AllowedAction`

Describes an available action.

| Field | Type | Description |
|-------|------|-------------|
| `action_type` | `str` | Action name |
| `description` | `str` | Human-readable description |
| `payload_schema` | `dict` | JSON schema for the payload |
