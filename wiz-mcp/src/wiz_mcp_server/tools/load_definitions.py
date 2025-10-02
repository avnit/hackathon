"""
Tool Definition Loading.

This module provides functions to load tool definitions from various sources.
"""

from typing import List, Optional

from wiz_mcp_server.utils.logger import get_logger
# Then import the implementations
from .local_tool_definition_loader import LocalToolDefinitionLoader
from .remote_tool_definition_loader import RemoteToolDefinitionLoader
from .tool_definition_classes import ToolDefinition
# Import the base classes first to avoid circular imports
from .tool_definition_loader import ToolDefinitionLoader

logger = get_logger()


def get_loader(source_type: str = "local") -> ToolDefinitionLoader:
    """
    Get the appropriate tool definition loader based on the source type.

    Args:
        source_type: Type of source ("local" or "remote")

    Returns:
        ToolDefinitionLoader: The appropriate loader
    """
    if source_type.lower() == "remote":
        return RemoteToolDefinitionLoader()
    else:
        return LocalToolDefinitionLoader()


def load_tool_definitions(
        source_location: str,
        source_type: str = "local"
) -> List[ToolDefinition]:
    """
    Load all tool definitions from the specified source.

    Args:
        source_location: Location containing tool definitions
        source_type: Type of source ("local" or "remote")

    Returns:
        List[ToolDefinition]: List of tool definitions
    """
    loader = get_loader(source_type)
    return loader.load_all_definitions(source_location)


def load_tool_definition(
        source_identifier: str,
        source_type: str = "local"
) -> Optional[ToolDefinition]:
    """
    Load a single tool definition from the specified source.

    Args:
        source_identifier: Identifier for the source
        source_type: Type of source ("local" or "remote")

    Returns:
        Optional[ToolDefinition]: The tool definition or None if it could not be loaded
    """
    loader = get_loader(source_type)
    return loader.load_definition(source_identifier)
