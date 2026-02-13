"""MCP server: tool definitions and stub handlers."""

import json
import logging
import uuid
from typing import Any

from mcp import types
from mcp.server.lowlevel import Server

from neg_env.core.match import MatchStatus
from neg_env.core.runner import MatchRunner
from neg_env.games import get_game_spec, list_game_ids
from neg_env.games.builtins import ensure_builtins_registered

logger = logging.getLogger(__name__)


def get_tool_definitions() -> list[types.Tool]:
    """Return the MCP tool list (for tests and for list_tools handler). Uses inputSchema (camelCase) for client compatibility."""
    return [
        types.Tool(
            name="list_games",
            description="List available game ids",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_game_rules",
            description="Get rules and spec for a game by id",
            inputSchema={
                "type": "object",
                "required": ["game_id"],
                "properties": {"game_id": {"type": "string", "description": "Game id"}},
            },
        ),
        types.Tool(
            name="start_game",
            description="Create a new match for a game; returns match_id and your agent_id",
            inputSchema={
                "type": "object",
                "required": ["game_id"],
                "properties": {"game_id": {"type": "string", "description": "Game id"}},
            },
        ),
        types.Tool(
            name="join_game",
            description="Join an existing match by invite/code; returns your agent_id",
            inputSchema={
                "type": "object",
                "required": ["match_id", "invite_code"],
                "properties": {
                    "match_id": {"type": "string"},
                    "invite_code": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_turn_state",
            description="Get current game state, messages, and allowed actions for your turn",
            inputSchema={
                "type": "object",
                "required": ["match_id", "agent_id"],
                "properties": {
                    "match_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="send_public_message",
            description="Send a message visible to all agents",
            inputSchema={
                "type": "object",
                "required": ["match_id", "agent_id", "content"],
                "properties": {
                    "match_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="send_private_message",
            description="Send a message to specific agent(s) only",
            inputSchema={
                "type": "object",
                "required": ["match_id", "agent_id", "content", "to_agent_ids"],
                "properties": {
                    "match_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "content": {"type": "string"},
                    "to_agent_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
        ),
        types.Tool(
            name="perform_action",
            description="Perform a game action (e.g. submit_offer, place_bid, accept)",
            inputSchema={
                "type": "object",
                "required": ["match_id", "agent_id", "action_type", "payload"],
                "properties": {
                    "match_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "action_type": {"type": "string"},
                    "payload": {"type": "object"},
                },
            },
        ),
    ]


def create_app(runner: MatchRunner | None = None) -> Server:
    """Create the MCP Server with all tools. Optionally pass a shared MatchRunner."""
    ensure_builtins_registered()
    app = Server("neg-env")
    _runner = runner or MatchRunner()

    def _log_event(match_id: str, event: str, **kwargs: Any) -> None:
        logger.info("neg_env event=%s match_id=%s %s", event, match_id, " ".join(f"{k}={v!r}" for k, v in kwargs.items()))
        _runner.record_match_event(match_id, event, **kwargs)

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return get_tool_definitions()

    @app.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.ContentBlock]:
        if name == "list_games":
            result = list_game_ids()
            return [types.TextContent(type="text", text=str(result))]
        if name == "get_game_rules":
            game_id = arguments.get("game_id", "")
            spec = get_game_spec(game_id)
            if spec is None:
                return [types.TextContent(type="text", text=f"Unknown game: {game_id}")]
            return [types.TextContent(type="text", text=spec.model_dump_json())]
        if name == "start_game":
            game_id = arguments.get("game_id", "")
            spec = get_game_spec(game_id)
            if spec is None:
                return [types.TextContent(type="text", text=json.dumps({"error": f"Unknown game: {game_id}"}))]
            match_id = uuid.uuid4().hex
            agent_id = f"agent_{uuid.uuid4().hex[:8]}"
            _runner.create_match(match_id, game_id, spec, [agent_id])
            _log_event(match_id, "match_created", game_id=game_id, agent_id=agent_id)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "match_id": match_id,
                        "agent_id": agent_id,
                        "invite_code": match_id,
                    }),
                )
            ]
        if name == "join_game":
            match_id = arguments.get("match_id", "")
            invite_code = arguments.get("invite_code", "")
            match = _runner.get_match(match_id)
            if match is None:
                return [types.TextContent(type="text", text=json.dumps({"error": f"Match not found: {match_id}"}))]
            if invite_code != match_id:
                return [types.TextContent(type="text", text=json.dumps({"error": "Invalid invite_code"}))]
            agent_id = f"agent_{uuid.uuid4().hex[:8]}"
            match.agent_ids.append(agent_id)
            min_agents = getattr(match.spec, "min_agents", 1)
            if len(match.agent_ids) >= min_agents and match.status == MatchStatus.WAITING:
                match.status = MatchStatus.RUNNING
            _log_event(match_id, "agent_joined", agent_id=agent_id, participant_count=len(match.agent_ids))
            return [types.TextContent(type="text", text=json.dumps({"agent_id": agent_id}))]
        if name == "get_turn_state":
            match_id = arguments.get("match_id", "")
            agent_id = arguments.get("agent_id", "")
            ts = _runner.get_turn_state(match_id, agent_id)
            if ts is None:
                return [types.TextContent(type="text", text=json.dumps({"error": "Match not found or agent not in match"}))]
            return [types.TextContent(type="text", text=ts.model_dump_json())]
        if name == "send_public_message":
            match_id = arguments.get("match_id", "")
            agent_id = arguments.get("agent_id", "")
            content = arguments.get("content", "")
            result = _runner.send_public_message(match_id, agent_id, content)
            if result.ok:
                _log_event(match_id, "public_message", agent_id=agent_id, content=content[:200])
            return [types.TextContent(type="text", text=result.model_dump_json())]
        if name == "send_private_message":
            match_id = arguments.get("match_id", "")
            agent_id = arguments.get("agent_id", "")
            content = arguments.get("content", "")
            to_agent_ids = arguments.get("to_agent_ids", [])
            if not isinstance(to_agent_ids, list):
                to_agent_ids = []
            result = _runner.send_private_message(match_id, agent_id, content, to_agent_ids)
            if result.ok:
                _log_event(match_id, "private_message", agent_id=agent_id, to_agent_ids=to_agent_ids, content=content[:200])
            return [types.TextContent(type="text", text=result.model_dump_json())]
        if name == "perform_action":
            match_id = arguments.get("match_id", "")
            agent_id = arguments.get("agent_id", "")
            action_type = arguments.get("action_type", "")
            payload = arguments.get("payload", {})
            if not isinstance(payload, dict):
                payload = {}
            result = _runner.perform_action(match_id, agent_id, action_type, payload)
            if result.ok:
                _log_event(match_id, "action_applied", agent_id=agent_id, action_type=action_type, payload=payload)
            return [types.TextContent(type="text", text=result.model_dump_json())]
        raise ValueError(f"Unknown tool: {name}")

    return app


async def run_server(
    transport: str = "sse",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Run the MCP server. transport: stdio | sse. With sse, one server serves many clients."""
    import sys

    if transport == "stdio":
        app = create_app()
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            print("neg_env MCP server ready. Waiting for client on stdio.", file=sys.stderr)
            await app.run(read_stream, write_stream, app.create_initialization_options())
        return

    if transport != "sse":
        raise ValueError("transport must be 'stdio' or 'sse'")

    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import HTMLResponse, JSONResponse, Response
    from starlette.routing import Mount, Route

    runner = MatchRunner()
    app = create_app(runner)
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> Response:
        async with sse.connect_sse(
            request.scope, request.receive, request._send  # noqa: SLF001
        ) as streams:
            await app.run(
                streams[0], streams[1], app.create_initialization_options(), stateless=True
            )
        return Response()

    async def list_matches(_request: Request) -> Response:
        matches = [
            {"match_id": mid, "game_id": m.game_id, "status": m.status.value, "agent_ids": m.agent_ids}
            for mid, m in runner._matches.items()
        ]
        return JSONResponse(matches)

    async def get_match(request: Request) -> Response:
        match_id = request.path_params.get("match_id", "")
        match = runner.get_match(match_id)
        if match is None:
            return JSONResponse({"error": "Match not found"}, status_code=404)
        out = match.model_dump(mode="json")
        out["events"] = runner.get_match_events(match_id)
        return JSONResponse(out)

    def dashboard_html() -> str:
        return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>neg_env dashboard</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 0; padding: 1rem; background: #0f0f12; color: #e4e4e7; }
    h1 { font-size: 1.25rem; margin-bottom: 1rem; }
    .refresh { font-size: 0.75rem; color: #71717a; margin-left: 0.5rem; }
    .grid { display: grid; grid-template-columns: 280px 1fr; gap: 1rem; min-height: 80vh; }
    .panel { background: #18181b; border-radius: 8px; padding: 1rem; overflow: auto; }
    .panel h2 { font-size: 0.9rem; margin: 0 0 0.75rem; color: #a1a1aa; }
    .match-list { list-style: none; padding: 0; margin: 0; }
    .match-list li { padding: 0.5rem 0.75rem; margin-bottom: 2px; border-radius: 6px; cursor: pointer; }
    .match-list li:hover { background: #27272a; }
    .match-list li.selected { background: #3f3f46; }
    .match-list .mid { font-family: monospace; font-size: 0.8rem; color: #71717a; }
    .match-list .meta { font-size: 0.8rem; margin-top: 2px; }
    .detail-section { margin-bottom: 1.25rem; }
    .detail-section h3 { font-size: 0.8rem; color: #71717a; margin: 0 0 0.5rem; text-transform: uppercase; }
    .detail-section pre { background: #27272a; padding: 0.75rem; border-radius: 6px; font-size: 0.8rem; overflow-x: auto; margin: 0; white-space: pre-wrap; }
    .events-list { font-size: 0.85rem; }
    .events-list { max-height: 320px; overflow-y: auto; }
    .events-list .ev { padding: 0.4rem 0; border-bottom: 1px solid #27272a; display: flex; flex-wrap: wrap; gap: 0.35rem 0.5rem; align-items: baseline; }
    .events-list .ts { color: #71717a; font-family: monospace; font-size: 0.75rem; flex-shrink: 0; }
    .events-list .evt { font-weight: 600; }
    .events-list .ev-action .action-type { color: #a78bfa; font-weight: 500; }
    .events-list .ev-msg .msg-content { color: #e4e4e7; }
    .empty { color: #71717a; font-style: italic; }
  </style>
</head>
<body>
  <h1>neg_env dashboard <span class="refresh">(auto-refresh 2s)</span></h1>
  <div class="grid">
    <div class="panel">
      <h2>Matches</h2>
      <ul class="match-list" id="match-list"></ul>
    </div>
    <div class="panel">
      <h2>Match detail</h2>
      <div id="match-detail"><span class="empty">Select a match</span></div>
    </div>
  </div>
  <script>
    const listEl = document.getElementById('match-list');
    const detailEl = document.getElementById('match-detail');
    let selectedId = null;

    function renderMatch(m) {
      const li = document.createElement('li');
      li.dataset.id = m.match_id;
      li.className = selectedId === m.match_id ? 'selected' : '';
      li.innerHTML = '<div class="mid">' + m.match_id.slice(0, 12) + '…</div><div class="meta">' + m.game_id + ' · ' + m.status + ' · ' + (m.agent_ids?.length || 0) + ' agents</div>';
      li.onclick = () => { selectedId = m.match_id; refresh(); loadDetail(m.match_id); };
      return li;
    }

    async function refresh() {
      try {
        const r = await fetch('/matches');
        const matches = await r.json();
        listEl.innerHTML = '';
        matches.forEach(m => listEl.appendChild(renderMatch(m)));
      } catch (e) { listEl.innerHTML = '<li class="empty">Failed to load matches</li>'; }
    }

    function fmtTs(ts) { const d = new Date(ts * 1000); return d.toLocaleTimeString(); }
    function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

    function renderEvent(ev) {
      const ts = '<span class="ts">' + esc(fmtTs(ev.timestamp)) + '</span>';
      if (ev.event === 'action_applied') {
        const agent = esc(ev.agent_id || '?');
        const action = esc(ev.action_type || '?');
        const payload = ev.payload ? ' ' + esc(JSON.stringify(ev.payload)) : '';
        return '<div class="ev ev-action">' + ts + '<span class="evt">' + agent + '</span> <span class="action-type">' + action + '</span>' + (payload ? '<span class="meta">' + payload + '</span>' : '') + '</div>';
      }
      if (ev.event === 'public_message' || ev.event === 'private_message') {
        const agent = esc(ev.agent_id || '?');
        const content = esc((ev.content || '').slice(0, 120) + ((ev.content && ev.content.length > 120) ? '\u2026' : ''));
        const to = ev.to_agent_ids && ev.to_agent_ids.length ? ' \u2192 ' + esc(ev.to_agent_ids.join(',')) : '';
        return '<div class="ev ev-msg">' + ts + '<span class="evt">' + agent + '</span> ' + (ev.event === 'private_message' ? '<span class="meta">(private' + to + ')</span> ' : '') + '<span class="msg-content">' + content + '</span></div>';
      }
      if (ev.event === 'match_created' || ev.event === 'agent_joined') {
        const rest = Object.keys(ev).filter(k => !['event','timestamp'].includes(k)).map(k => k + '=' + JSON.stringify(ev[k])).join(' ');
        return '<div class="ev">' + ts + '<span class="evt">' + esc(ev.event) + '</span>' + (rest ? ' <span class="meta">' + esc(rest) + '</span>' : '') + '</div>';
      }
      const rest = Object.keys(ev).filter(k => !['event','timestamp'].includes(k)).map(k => k + '=' + JSON.stringify(ev[k])).join(' ');
      return '<div class="ev">' + ts + '<span class="evt">' + esc(ev.event) + '</span>' + (rest ? ' <span class="meta">' + esc(rest) + '</span>' : '') + '</div>';
    }

    async function loadDetail(matchId) {
      try {
        const r = await fetch('/match/' + matchId);
        const m = await r.json();
        let html = '';
        html += '<div class="detail-section"><h3>Status & agents</h3><pre>' + JSON.stringify({ status: m.status, agent_ids: m.agent_ids, current_round: m.current_round, current_turn_index: m.current_turn_index }, null, 2) + '</pre></div>';
        const events = m.events || [];
        html += '<div class="detail-section"><h3>Event log — actions & messages (' + events.length + ')</h3><div class="events-list">';
        if (events.length === 0) html += '<span class="empty">No events yet (actions and chat will appear here)</span>';
        else events.forEach(ev => { html += renderEvent(ev); });
        html += '</div></div>';
        html += '<div class="detail-section"><h3>Game state</h3><pre>' + JSON.stringify(m.game_state || {}, null, 2) + '</pre></div>';
        html += '<div class="detail-section"><h3>Chat (messages)</h3><pre>' + JSON.stringify((m.messages || []).map(msg => ({ from: msg.sender_id, scope: msg.scope, to: msg.to_agent_ids, content: msg.content })), null, 2) + '</pre></div>';
        detailEl.innerHTML = html;
      } catch (e) { detailEl.innerHTML = '<span class="empty">Failed to load match</span>'; }
    }

    refresh();
    setInterval(() => { refresh(); if (selectedId) loadDetail(selectedId); }, 2000);
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') { refresh(); if (selectedId) loadDetail(selectedId); } });
  </script>
</body>
</html>"""

    async def dashboard(_request: Request) -> Response:
        return HTMLResponse(dashboard_html())

    starlette_app = Starlette(
        debug=False,
        routes=[
            Route("/", dashboard, methods=["GET"]),
            Route("/dashboard", dashboard, methods=["GET"]),
            Route("/sse", handle_sse, methods=["GET"]),
            Route("/matches", list_matches, methods=["GET"]),
            Route("/match/{match_id}", get_match, methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )
    import uvicorn

    print(
        f"neg_env MCP server (SSE) at http://{host}:{port} — one server, many clients.",
        file=sys.stderr,
    )
    print(f"  GET  http://{host}:{port}/sse  (establish SSE)", file=sys.stderr)
    print(f"  POST http://{host}:{port}/messages/?session_id=... (send messages)", file=sys.stderr)
    print(f"  GET  http://{host}:{port}/  or  /dashboard  (server dashboard)", file=sys.stderr)
    print(f"  GET  http://{host}:{port}/matches  (list matches)", file=sys.stderr)
    print(f"  GET  http://{host}:{port}/match/{{match_id}}  (match state + events)", file=sys.stderr)
    config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
