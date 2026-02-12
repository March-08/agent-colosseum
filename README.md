# Neg Env – Negotiation Environment

Multi-agent negotiation environment: agents connect via MCP to play economic strategy games (bargaining, auctions, etc.).

- **Game spec**: each game defines conversation model, outcome resolution, state, and actions.
- **MCP server**: single interface; agents use tools to get state, send messages, and perform actions.
- **Python 3.10+**.

## One server, many clients

You run **one** neg_env server (e.g. on localhost). **Multiple MCP clients** connect to it to create matches, join games, and play. The server holds all match state.

- **SSE (default)**: You run the server once; it listens on `http://127.0.0.1:8000`. All clients connect to that URL. One process, shared matches — use this for multi-agent play.
- **stdio**: The client spawns the server as a subprocess (one process per client). Use for single-client tools like Cursor that expect stdio.

## Install

```bash
pip install -e .
```

## Run the server

**SSE (default) — one server, many clients (recommended):**

```bash
python -m neg_env
# Or: python -m neg_env --transport sse --host 127.0.0.1 --port 8000
```

The server listens on `http://127.0.0.1:8000`. You should see on **stderr**:

- `neg_env MCP server (SSE) at http://127.0.0.1:8000 — one server, many clients.`
- `GET  http://127.0.0.1:8000/sse` and `POST http://127.0.0.1:8000/messages/...`

Leave this process running. All MCP clients that connect to this URL share the same match state.

**stdio — one process per client (e.g. for Cursor):**

```bash
python -m neg_env --transport stdio
```

The process then waits for a single client on stdin/stdout. Typically you don’t run this yourself; Cursor runs it when you add the MCP server with stdio.

## Connecting clients

### Cursor with SSE (recommended: one server, many clients)

1. **Start the server** in a terminal (leave it running):
   ```bash
   python -m neg_env --transport sse --host 127.0.0.1 --port 8000
   ```

2. **In Cursor**: **Settings → Features → MCP** (or **Settings → MCP**).

3. Click **Add new MCP server**.

4. Set **Type** to **SSE** (not stdio).

5. Set **Server URL** to:
   ```text
   http://127.0.0.1:8000/sse
   ```
   (Use `http://localhost:8000/sse` if you prefer; use another port if you started the server with `--port 8001`.)

6. Save and, if needed, refresh MCP. The tools (`list_games`, `start_game`, `get_turn_state`, etc.) should appear. Every Cursor window (or agent) that adds this server will connect to the **same** running process and share matches.

**Optional — edit `mcp.json` directly** (e.g. in `~/.cursor/mcp.json` or your project’s MCP config):

```json
{
  "mcpServers": {
    "neg-env": {
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

No auth token is required for localhost. If your Cursor build only offers “command” and not “url”, use the stdio setup below and run the server with stdio (one process per client).

### Other SSE/HTTP clients

Point any MCP client that supports **SSE** at the server URL. The client opens GET `http://127.0.0.1:8000/sse`, then POSTs messages to `/messages/?session_id=...`. The MCP SDK handles this when you configure the server URL as above.

### stdio: Cursor or other single-client tools

1. **Cursor Settings → MCP → Add new MCP server**.
2. **Type**: stdio.
3. **Command**: `python` (or your venv’s `python`).
4. **Args**: `["-m", "neg_env", "--transport", "stdio"]`.

Example config:

```json
{
  "mcpServers": {
    "neg-env": {
      "command": "python",
      "args": ["-m", "neg_env", "--transport", "stdio"]
    }
  }
}
```

Cursor will start one neg_env process when it uses this server; that process is only for that Cursor session. For multiple agents playing the same game, run the server with SSE and connect clients to `http://127.0.0.1:8000`.

## Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

- `tests/test_core.py` – match runner, create_match, get_turn_state, apply_message
- `tests/test_game_split100.py` – Split100 game flow (offer, accept, reject, outcome)
- `tests/conftest.py` – registers built-in games for tests

## Project layout

- `neg_env.types` – shared types (Message, Action, TurnState, etc.)
- `neg_env.spec` – game spec schema (GameSpec, Phase, action types)
- `neg_env.core` – match runner and match state
- `neg_env.games` – game implementations (split-$100, auction, …)
- `neg_env.server` – MCP server and tool handlers
