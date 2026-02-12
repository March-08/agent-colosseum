"""Entry point: run the MCP server (stdio)."""

import asyncio
import sys


def main() -> int:
    """Run the neg_env MCP server on stdio."""
    try:
        from neg_env.server import run_server

        asyncio.run(run_server(transport="stdio"))
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
