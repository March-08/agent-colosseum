"""Tests for MCP server tool definitions (regression: inputSchema, tool list)."""

import pytest

from neg_env.server.mcp_server import get_tool_definitions


EXPECTED_TOOL_NAMES = {
    "list_games",
    "get_game_rules",
    "start_game",
    "join_game",
    "get_turn_state",
    "send_public_message",
    "send_private_message",
    "perform_action",
}


def test_tool_definitions_count() -> None:
    """We expose exactly the expected number of tools."""
    tools = get_tool_definitions()
    assert len(tools) == len(EXPECTED_TOOL_NAMES)


def test_tool_definitions_names() -> None:
    """Tool names match the expected set (no missing/extra)."""
    tools = get_tool_definitions()
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOL_NAMES


def test_tool_definitions_use_input_schema_camel_case() -> None:
    """Each tool exposes inputSchema (camelCase) in serialized form so clients (e.g. Cursor) see tools."""
    tools = get_tool_definitions()
    for t in tools:
        d = t.model_dump()
        assert "inputSchema" in d, f"Tool {t.name!r} must expose inputSchema (camelCase) for MCP clients"
        assert isinstance(d["inputSchema"], dict), f"Tool {t.name!r} inputSchema must be a dict (JSON schema)"
        assert d["inputSchema"].get("type") == "object", f"Tool {t.name!r} inputSchema must be type object"
