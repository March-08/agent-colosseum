# Agents

neg-env ships with two built-in agents. You can also [write your own](custom-agents.md).

| Agent | Description |
|-------|-------------|
| `RandomAgent(agent_id, seed)` | Picks a random allowed action each turn. Useful for testing and baselines. |
| [`LangChainNegotiationAgent`](llm-agents.md) | Game-agnostic LLM agent. You supply a system prompt; it receives game state and returns actions. Supports OpenAI and OpenRouter. |

## Agent interface

| Method | Required | Description |
|--------|----------|-------------|
| `agent_id` (property) | Yes | Unique string identifier |
| `act(state: TurnState) -> AgentResponse` | Yes | Observe game state, return messages + one game action |
| `on_match_start(match_id, game_id, agent_ids)` | No | Called before a match begins |
| `on_match_end(match_id, outcome)` | No | Called after a match ends |

## Turn model

Each turn, the current agent receives a `TurnState` and returns an `AgentResponse`:

- **Messages** (`AgentResponse.messages`) are delivered first. They do **not** consume a turn. You can send zero or more messages per turn (capped by `max_messages_per_turn`).
- **Action** (`AgentResponse.action`) is the game action (e.g. `submit_offer`, `accept`, `submit_bid`). This advances the turn.
- **`message_only`** is a special action that does not advance the turn. When an agent uses it, the other agent is pinged to reply. This allows multi-turn chat before committing to a game action.
