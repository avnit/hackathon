"""
Local Tool Definition Loader.

This module provides functionality to load tool definitions from local YAML files.
"""

import os
from typing import List, Optional

from wiz_mcp_server.utils.logger import get_logger
from .tool_definition_classes import ToolDefinition
from .tool_definition_loader import ToolDefinitionLoader
from .tool_definition_utils import parse_yaml_to_tool_definition

logger = get_logger()


class LocalToolDefinitionLoader(ToolDefinitionLoader):
    """Loader for tool definitions from local YAML files."""

    def load_definition(self, source_identifier: str) -> Optional[ToolDefinition]:
        """
        Load a tool definition from a local YAML file.

        Args:
            source_identifier: Path to the YAML file

        Returns:
            ToolDefinition or None if the file could not be loaded
        """
        try:
            with open(source_identifier, 'r') as f:
                yaml_content = f.read()

            return parse_yaml_to_tool_definition(yaml_content, source_identifier)

        except Exception as e:
            logger.error(f"Error loading tool definition from {source_identifier}: {e}")
            return None

    def load_all_definitions(self, source_location: str) -> List[ToolDefinition]:
        """
        Load all tool definitions from YAML files in a local directory.

        Args:
            source_location: Directory containing YAML files

        Returns:
            List of tool definitions
        """
        tool_defs = []

        # Get all YAML files in the directory
        yaml_files = [f for f in os.listdir(source_location) if f.endswith('.yaml')]

        for yaml_file in yaml_files:
            yaml_path = os.path.join(source_location, yaml_file)

            # Load the tool definition
            tool_def = self.load_definition(yaml_path)
            if tool_def:
                tool_defs.append(tool_def)

        return tool_defs
