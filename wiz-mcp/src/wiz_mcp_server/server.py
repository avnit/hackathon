"""
Server module for the Wiz MCP Server.

This module provides the FastMCP server for the Wiz MCP Server, which enables
interaction with the Wiz cloud security platform through the Model Context Protocol.
The server exposes tools for retrieving and analyzing security issues and their
remediation strategies.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from wiz_mcp_server.auth.auth import authenticate
from wiz_mcp_server.utils.context import WizContext
from wiz_mcp_server.utils.logger import get_logger

# Global constants
SERVER_NAME = "Wiz MCP Server"
SERVER_DESCRIPTION = "A Model Context Protocol (MCP) server for the Wiz API"

logger = get_logger()


def validate_env(required_vars: Optional[List[str]] = None) -> None:
    """Validate that required environment variables are set.

    Args:
        required_vars: List of environment variables that must be set

    Raises:
        ValueError: If any required environment variable is not set
    """
    if required_vars is None:
        required_vars = ["WIZ_CLIENT_ID", "WIZ_CLIENT_SECRET"]

    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        if len(missing_vars) == 1:
            raise ValueError(f"{missing_vars[0]} environment variable must be set")
        else:
            raise ValueError(f"The following environment variables must be set: {', '.join(missing_vars)}")


def load_environment(env_file_path=None):
    """Load environment variables from .env file."""
    important_vars = ["WIZ_CLIENT_ID", "WIZ_CLIENT_SECRET", "WIZ_ENV"]
    initial_vars = {var: os.environ.get(var) for var in important_vars}

    # Try loading from specified path, environment variable, current directory, or script directory
    if env_file_path:
        if os.path.exists(env_file_path):
            dotenv_path = os.path.abspath(env_file_path)
        else:
            logger.error(f"Specified .env file not found: {env_file_path}")
            raise FileNotFoundError(f"Specified .env file not found: {env_file_path}")
    else:
        # Check for WIZ_DOTENV_PATH environment variable
        env_path = os.environ.get("WIZ_DOTENV_PATH")
        if env_path and os.path.exists(env_path):
            dotenv_path = os.path.abspath(env_path)
            logger.info(f"Using .env file from WIZ_DOTENV_PATH environment variable: {dotenv_path}")
        else:
            cwd_path = os.path.join(os.getcwd(), ".env")
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

            if os.path.exists(cwd_path):
                dotenv_path = cwd_path
            elif os.path.exists(script_path):
                dotenv_path = script_path
            else:
                logger.info("No .env file found")
                dotenv_path = None

    # Load the .env file if found
    if dotenv_path:
        logger.info(f"Loading environment variables from: {dotenv_path}")
        load_dotenv(dotenv_path)

        # Log which variables were loaded
        loaded = [var for var in important_vars
                  if os.environ.get(var) and initial_vars[var] != os.environ.get(var)]
        if loaded:
            logger.info(f"Loaded variables: {', '.join(loaded)}")

    # Log the current WIZ_ENV value
    logger.info(f"Using Wiz environment: {os.environ.get('WIZ_ENV', 'app')}")


@asynccontextmanager
async def wiz_lifespan(mcp_server: FastMCP) -> AsyncIterator[WizContext]:
    """
    Manage application lifecycle with type-safe context.

    Args:
        mcp_server: FastMCP server

    Yields:
        WizContext: Wiz context

    Raises:
        ValueError: If required environment variables are not set
        Exception: If there's an error during authentication or tool registration
    """
    # Initialize on startup - authenticate with Wiz API
    try:
        # Validate required environment variables
        validate_env(["WIZ_CLIENT_ID", "WIZ_CLIENT_SECRET"])

        # Authenticate with Wiz API
        auth_result = await authenticate()
        context = WizContext(
            auth_headers=auth_result.auth_headers,
            data_center=auth_result.data_center,
            env=auth_result.env
        )

        # Register dynamic tools
        try:
            from wiz_mcp_server.tools import register_dynamic_tools, register_wiz_search_tool
            register_dynamic_tools(mcp_server)
            logger.info("Registered dynamic tools successfully post authentication.")

            # Register our special wiz_search tool
            register_wiz_search_tool(mcp_server)
            logger.info("Registered wiz_search tool (if applicable).")
        except Exception as e:
            logger.error(f"Error registering tools: {e}")
            import traceback
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception traceback: {traceback.format_exc()}")
            # Re-raise the exception with a clearer message
            raise Exception(f"Failed to register tools: {e}") from e

        yield context
    except Exception as e:
        # Log the error and re-raise
        logger.error(f"Error during mcp server initialization: {e}")
        raise


# Track if environment has been loaded
_env_loaded = False


def create_server(env_file_path=None) -> FastMCP:
    """
    Create a configured FastMCP server instance for the Wiz API.

    This function creates and configures a FastMCP server with the appropriate
    lifespan context manager and registers all available Wiz API tools.

    Args:
        env_file_path: Optional path to a .env file containing environment variables

    Returns:
        FastMCP: Configured FastMCP server instance ready to be run
    """
    global server, _env_loaded

    # Only load environment if it hasn't been loaded yet or if a specific path is provided
    if not _env_loaded or env_file_path:
        load_environment(env_file_path)
        _env_loaded = True

    # Create the server instance
    mcp = FastMCP(
        SERVER_NAME,
        lifespan=wiz_lifespan,
    )

    # Update the module-level server variable
    server = mcp

    return mcp


# Initialize the server with default settings
# This is used when the module is imported directly
server = create_server()

# Entry point for direct execution
if __name__ == "__main__":
    from wiz_mcp_server.cli import main

    main()
