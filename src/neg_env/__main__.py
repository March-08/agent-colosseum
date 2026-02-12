"""Entry point: run the MCP server (SSE by default, or stdio)."""

import argparse
import asyncio
import sys


def main() -> int:
    """Run the neg_env MCP server. Default: SSE on localhost for one server, many clients."""
    parser = argparse.ArgumentParser(
        description="neg_env MCP server. Use SSE (default) for one server, many clients; use stdio for single-client (e.g. Cursor)."
    )
    parser.add_argument(
        "--transport",
        choices=["sse", "stdio"],
        default="sse",
        help="Transport: sse = one server, many clients (default); stdio = one process per client",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host for SSE (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE (default: 8000)")
    args = parser.parse_args()

    try:
        from neg_env.server import run_server

        if args.transport == "stdio":
            print("neg_env MCP server starting (stdio). One process per client.", file=sys.stderr)
        else:
            print(
                f"neg_env MCP server starting (SSE) at http://{args.host}:{args.port}.",
                file=sys.stderr,
            )
        asyncio.run(
            run_server(transport=args.transport, host=args.host, port=args.port)
        )
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
