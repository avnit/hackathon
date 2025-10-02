"""
Tool Definition Loader Interface.

This module provides the interface for loading tool definitions from various sources.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from wiz_mcp_server.utils.logger import get_logger
from .tool_definition_classes import ToolDefinition

logger = get_logger()


class ToolDefinitionLoader(ABC):
    """Interface for loading tool definitions from various sources."""

    @abstractmethod
    def load_definition(self, source_identifier: str) -> Optional[ToolDefinition]:
        """
        Load a single tool definition from the specified source.

        Args:
            source_identifier: Identifier for the source (e.g., file path, URL, etc.)

        Returns:
            ToolDefinition or None if the definition could not be loaded
        """
        pass

    @abstractmethod
    def load_all_definitions(self, source_location: str) -> List[ToolDefinition]:
        """
        Load all tool definitions from the specified source location.

        Args:
            source_location: Location containing tool definitions (e.g., directory, ZIP URL, etc.)

        Returns:
            List of tool definitions
        """
        pass
