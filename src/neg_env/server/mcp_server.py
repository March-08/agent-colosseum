"""MCP server: tool definitions and stub handlers."""

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


def create_app(runner: MatchRunner | None = None) -> Server:
    """Create the MCP Server with all tools. Optionally pass a shared MatchRunner."""
    _register_builtin_games()
    app = Server("neg-env")
    _runner = runner or MatchRunner()

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="list_games",
                description="List available game ids",
                input_schema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="get_game_rules",
                description="Get rules and spec for a game by id",
                input_schema={
                    "type": "object",
                    "required": ["game_id"],
                    "properties": {"game_id": {"type": "string", "description": "Game id"}},
                },
            ),
            types.Tool(
                name="start_game",
                description="Create a new match for a game; returns match_id and your agent_id",
                input_schema={
                    "type": "object",
                    "required": ["game_id"],
                    "properties": {"game_id": {"type": "string", "description": "Game id"}},
                },
            ),
            types.Tool(
                name="join_game",
                description="Join an existing match by invite/code; returns your agent_id",
                input_schema={
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
                input_schema={
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
                input_schema={
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
                input_schema={
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
                input_schema={
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
            raise NotImplementedError("start_game: create match via runner and return match_id, agent_id")
        if name == "join_game":
            raise NotImplementedError("join_game: validate invite, add agent, return agent_id")
        if name == "get_turn_state":
            raise NotImplementedError("get_turn_state: call runner.get_turn_state and return TurnState as JSON")
        if name == "send_public_message":
            raise NotImplementedError("send_public_message: call runner.send_public_message")
        if name == "send_private_message":
            raise NotImplementedError("send_private_message: call runner.send_private_message")
        if name == "perform_action":
            raise NotImplementedError("perform_action: call runner.perform_action")
        raise ValueError(f"Unknown tool: {name}")

    return app


async def run_server(transport: str = "stdio") -> None:
    """Run the MCP server. transport: stdio | sse (sse requires port)."""
    app = create_app()
    if transport == "stdio":
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    else:
        raise ValueError("Only stdio transport is implemented in the skeleton")
