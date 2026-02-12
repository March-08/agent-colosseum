# Neg Env – Negotiation Environment

Multi-agent negotiation environment: agents connect via MCP to play economic strategy games (bargaining, auctions, etc.).

- **Game spec**: each game defines conversation model, outcome resolution, state, and actions.
- **MCP server**: single interface; agents use tools to get state, send messages, and perform actions.
- **Python 3.10+**.

## Install

```bash
pip install -e .
```

## Run (once implemented)

```bash
python -m neg_env
# or: mcp run neg_env
```

## Project layout

- `neg_env.types` – shared types (Message, Action, TurnState, etc.)
- `neg_env.spec` – game spec schema (GameSpec, Phase, action types)
- `neg_env.core` – match runner and match state
- `neg_env.games` – game implementations (split-$100, auction, …)
- `neg_env.server` – MCP server and tool handlers
