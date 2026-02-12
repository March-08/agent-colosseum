"""MCP server: tool definitions and stub handlers."""

import json
import uuid
from typing import Any

from mcp import types
from mcp.server.lowlevel import Server

from neg_env.core.runner import MatchRunner
from neg_env.games import get_game_spec, list_game_ids, register_game
from neg_env.games.auction import SimpleAuctionGame
from neg_env.games.split100 import Split100Game


def _register_builtin_games() -> None:
    """Register built-in games so list_games / get_game_rules return them."""
    register_game(Split100Game())
    register_game(SimpleAuctionGame())


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
    _register_builtin_games()
    app = Server("neg-env")
    _runner = runner or MatchRunner()

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return get_tool_definitions()

    @app.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.ContentBlock]:
        # Stub implementations: return placeholder or raise
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
            ok = _runner.send_public_message(match_id, agent_id, content)
            return [types.TextContent(type="text", text=json.dumps({"ok": ok}))]
        if name == "send_private_message":
            match_id = arguments.get("match_id", "")
            agent_id = arguments.get("agent_id", "")
            content = arguments.get("content", "")
            to_agent_ids = arguments.get("to_agent_ids", [])
            if not isinstance(to_agent_ids, list):
                to_agent_ids = []
            ok = _runner.send_private_message(match_id, agent_id, content, to_agent_ids)
            return [types.TextContent(type="text", text=json.dumps({"ok": ok}))]
        if name == "perform_action":
            match_id = arguments.get("match_id", "")
            agent_id = arguments.get("agent_id", "")
            action_type = arguments.get("action_type", "")
            payload = arguments.get("payload", {})
            if not isinstance(payload, dict):
                payload = {}
            ok = _runner.perform_action(match_id, agent_id, action_type, payload)
            return [types.TextContent(type="text", text=json.dumps({"ok": ok}))]
        raise ValueError(f"Unknown tool: {name}")

    return app


async def run_server(
    transport: str = "sse",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Run the MCP server. transport: stdio | sse. With sse, one server serves many clients."""
    import sys

    app = create_app()
    if transport == "stdio":
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            print("neg_env MCP server ready. Waiting for client on stdio.", file=sys.stderr)
            await app.run(read_stream, write_stream, app.create_initialization_options())
    elif transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import Response
        from starlette.routing import Mount, Route

        sse = SseServerTransport("/messages/")

        async def handle_sse(request: Request) -> Response:
            async with sse.connect_sse(
                request.scope, request.receive, request._send  # noqa: SLF001
            ) as streams:
                await app.run(streams[0], streams[1], app.create_initialization_options())
            return Response()

        starlette_app = Starlette(
            debug=False,
            routes=[
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
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
        config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    else:
        raise ValueError("transport must be 'stdio' or 'sse'")
