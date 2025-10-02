"""
Tool Definition Utilities.

This module provides utility functions for working with tool definitions.
"""

from typing import Optional

import yaml

from wiz_mcp_server.utils.logger import get_logger
from .tool_definition_classes import ToolDefinition, ToolParameter
from ..utils import get_type_from_string

logger = get_logger()


def parse_yaml_to_tool_definition(yaml_content: str, source_identifier: str) -> Optional[ToolDefinition]:
    """
    Parse YAML content into a ToolDefinition object.

    Args:
        yaml_content: YAML content as a string
        source_identifier: Identifier for the source (for error logging)

    Returns:
        ToolDefinition or None if the content could not be parsed
    """
    try:
        tool_data = yaml.safe_load(yaml_content)

        # Extract basic information
        name = tool_data.get('name')
        description = tool_data.get('description')
        graphql_query = tool_data.get('gql_query')

        if not name or not description or not graphql_query:
            logger.error(f"Missing required fields in {source_identifier}")
            return None

        # Extract parameters
        parameters = []
        for param_name, param_data in tool_data.get('input_params', {}).items():
            param_type = get_type_from_string(param_data.get('type', 'string'))
            parameters.append(
                ToolParameter(
                    name=param_name,
                    type=param_type,
                    description=param_data.get('description', ''),
                    default=param_data.get('default'),
                    required=param_data.get('required', False)
                )
            )

        # Extract variable mapping
        variable_mapping = {}
        for param_name, mapping in tool_data.get('gql_mapping', {}).get('input_mapping', {}).items():
            if isinstance(mapping, dict):
                # Complex mapping - preserve the dictionary structure
                variable_mapping[param_name] = {'path': mapping.get('path')}
            else:
                # Simple mapping
                variable_mapping[param_name] = mapping

        # Extract default variables
        default_variables = tool_data.get('default_variables', {})

        # Extract disabled flag
        disabled = tool_data.get('disabled', False)

        # Create the tool definition
        tool_def = ToolDefinition(
            name=name,
            description=description,
            graphql_query=graphql_query,
            parameters=parameters,
            variable_mapping=variable_mapping,
            default_variables=default_variables,
            disabled=disabled
        )

        return tool_def

    except Exception as e:
        logger.error(f"Error parsing tool definition from {source_identifier}: {e}")
        return None
