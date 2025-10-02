#!/usr/bin/env python3
"""
Command-line interface for the Wiz MCP Server.

This module provides the command-line interface for running the Wiz MCP Server.
"""

import argparse
import asyncio
import os
import sys

from wiz_mcp_server.server import create_server
from wiz_mcp_server.utils.logger import get_logger
from wiz_mcp_server.version import __version__

logger = get_logger()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Wiz MCP Server")
    parser.add_argument(
        "--client-id",
        help="Wiz API client ID (taken from: WIZ_CLIENT_ID environment variable)",
        default=os.environ.get("WIZ_CLIENT_ID"),
    )
    parser.add_argument(
        "--client-secret",
        help="Wiz API client secret (taken from: WIZ_CLIENT_SECRET environment variable)",
        default=os.environ.get("WIZ_CLIENT_SECRET"),
    )
    parser.add_argument(
        "--wiz-env",
        help="Wiz environment (taken from: WIZ_ENV environment variable, defaults to 'app' if not set)",
        default=None,
        type=str,
    )
    parser.add_argument(
        "--env-file",
        help="Path to a .env file containing environment variables",
        type=str,
    )
    parser.add_argument(
        "--log-level",
        help="Log level (default: info)",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
    )
    parser.add_argument(
        "--version",
        help="Show version and exit",
        action="store_true",
    )
    parser.add_argument(
        "--execute-tool",
        help="Execute a specific tool directly instead of starting the server",
        type=str,
    )
    parser.add_argument(
        "--payload",
        help="Path to a YAML file containing the tool parameters",
        type=str,
    )
    parser.add_argument(
        "--disable-telemetry",
        help="Disable collection of telemetry data",
        action="store_true",
    )
    parser.add_argument(
        "--disable-remote-tools",
        help="Disable downloading tool definitions from remote source",
        action="store_true",
    )
    parser.add_argument(
        "--remote-tools-url",
        help="URL to download tool definitions from (taken from: WIZ_MCP_REMOTE_TOOLS_URL environment variable)",
        default=os.environ.get("WIZ_MCP_REMOTE_TOOLS_URL"),
    )
    return parser.parse_args()


def setup_env(args) -> None:
    """Set up environment variables from command-line arguments."""
    # Set environment variables for client ID and client secret if provided via command line
    if args.client_id:
        os.environ["WIZ_CLIENT_ID"] = args.client_id
    if args.client_secret:
        os.environ["WIZ_CLIENT_SECRET"] = args.client_secret

    # Only set WIZ_ENV if explicitly provided via command line
    if args.wiz_env is not None:
        os.environ["WIZ_ENV"] = args.wiz_env

    # Set log level from command line argument if provided
    if args.log_level:
        os.environ["LOG_LEVEL"] = args.log_level.upper()

    # Set telemetry collection flag
    if args.disable_telemetry:
        os.environ["WIZ_MCP_DISABLE_TELEMETRY"] = "true"

    # Set remote tools flags
    if args.disable_remote_tools:
        os.environ["WIZ_MCP_REMOTE_TOOLS_DISABLED"] = "true"
    if args.remote_tools_url:
        os.environ["WIZ_MCP_REMOTE_TOOLS_URL"] = args.remote_tools_url


def main() -> None:
    """Run the Wiz MCP Server."""
    # Parse arguments early to get log level
    args = parse_args()
    setup_env(args)

    if args.version:
        logger.info(f"Wiz MCP Server v{__version__}")
        sys.exit(0)

    # Check if we should execute a tool directly
    if args.execute_tool:
        if not args.payload:
            logger.error("--payload is required when using --execute-tool")
            sys.exit(1)

        # Import here to avoid circular imports
        from wiz_mcp_server.tools.execute_tool import execute_tool_directly

        # Execute the tool directly
        asyncio.run(execute_tool_directly(args.execute_tool, args.payload))
        return

    # Create the server instance
    server = create_server(env_file_path=args.env_file)

    # Run the server in stdio mode
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
