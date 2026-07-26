"""Executable entry point for the local LearnMate MCP server."""

from app.mcp_server import main, mcp

__all__ = ["main", "mcp"]


if __name__ == "__main__":
    main()
