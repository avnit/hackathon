"""
Tool Fetching for the Wiz MCP Server.

This module provides functionality to fetch tool definitions for the Wiz MCP Server.
"""

import datetime
import os
from typing import List

from wiz_mcp_server.utils.logger import get_logger
from .load_definitions import load_tool_definitions
from .remote_tool_definition_loader import ENCRYPTED_REMOTE_TOOLS_URL, decrypt
from .tool_cache import get_cached_tool_definitions, set_cached_tool_definitions
from .tool_definition_classes import ToolDefinition

# Logger
logger = get_logger()


def fetch_tools() -> List[ToolDefinition]:
    """
    Fetch the tool definitions for the Wiz MCP Server.

    This function returns a list of tool definitions that can be used to dynamically
    create tools for the Wiz MCP Server.

    The tool definitions are cached after the first call to avoid loading them multiple times.

    Returns:
        List[ToolDefinition]: List of tool definitions
    """
    # Return cached definitions if available
    cached_tools = get_cached_tool_definitions()
    if cached_tools is not None:
        logger.info("Using cached tool definitions - skipping remote loading")
        return cached_tools
    # Check if remote tools are enabled (enabled by default)
    remote_tools_disabled = os.environ.get("WIZ_MCP_REMOTE_TOOLS_DISABLED", "false").lower()
    remote_tools_enabled = remote_tools_disabled not in ("true", "1", "yes", "y", "on")

    # Get the remote tools URL from the environment
    remote_tools_url = os.environ.get("WIZ_MCP_REMOTE_TOOLS_URL")

    # If no URL is provided but remote tools are enabled, try to decrypt the default URL
    if not remote_tools_url and remote_tools_enabled and ENCRYPTED_REMOTE_TOOLS_URL:
        # Try to get the decryption key from the environment (set during authentication)
        decryption_key = os.environ.get("WIZ_MCP_REMOTE_TOOLS_KEY", "")

        if decryption_key:
            try:
                # Decrypt the URL using the key
                remote_tools_url = decrypt(ENCRYPTED_REMOTE_TOOLS_URL, decryption_key)
                logger.info("Successfully decrypted remote tools URL using organization credentials")
            except Exception as e:
                logger.warning(f"Failed to decrypt default URL: {e}")
                remote_tools_url = None
        else:
            logger.warning("Remote tools are enabled but no URL is provided and no decryption key is available.")
            logger.warning("Please either set WIZ_MCP_REMOTE_TOOLS_URL manually or use the Wiz MCP integration.")
            remote_tools_url = None

    # If we still don't have a URL, disable remote tools
    if not remote_tools_url and remote_tools_enabled:
        logger.warning("Remote tools are enabled but no URL is available. Disabling remote tools.")
        remote_tools_enabled = False

    tools = []

    # Try to load from remote source first if enabled
    if remote_tools_enabled:
        try:
            logger.info("Attempting to load tool definitions from remote source")
            tools = load_tool_definitions(remote_tools_url, "remote")
            if tools:
                logger.info(f"Successfully loaded {len(tools)} tool definitions from remote source")
                # Set environment variable to indicate remote tools are being used
                os.environ["WIZ_MCP_USING_REMOTE_TOOLS"] = "true"

                # Add source and timestamp to tool descriptions
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for tool in tools:
                    tool.description = f"{tool.description} [Remote: {timestamp}]"

                return tools
            else:
                logger.warning("No tool definitions found from remote source, falling back to local definitions")
        except Exception as e:
            logger.warning(f"Failed to load tool definitions from remote source: {e}")
            logger.info("Falling back to local tool definitions")
    else:
        logger.info("Remote tool definitions are disabled, using local definitions")

    # Fall back to local tool definitions
    current_dir = os.path.dirname(os.path.abspath(__file__))
    tool_defs_dir = os.path.join(current_dir, 'tool_definitions')

    # Load all tool definitions from local YAML files
    tools = load_tool_definitions(tool_defs_dir, "local")
    logger.info(f"Loaded {len(tools)} tool definitions from local directory: {tool_defs_dir}")

    # Set environment variable to indicate local tools are being used
    os.environ["WIZ_MCP_USING_REMOTE_TOOLS"] = "false"

    # Add source and timestamp to tool descriptions
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for tool in tools:
        tool.description = f"{tool.description} [Local: {timestamp}]"

    # Cache the tool definitions for future calls
    set_cached_tool_definitions(tools)

    return tools
