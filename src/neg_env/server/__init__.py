"""MCP server: exposes tools for agents to list games, join matches, get state, send messages, perform actions."""

from neg_env.server.mcp_server import create_app, run_server

__all__ = ["create_app", "run_server"]
