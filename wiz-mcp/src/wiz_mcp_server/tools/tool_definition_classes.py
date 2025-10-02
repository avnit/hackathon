"""
Tool Definitions for the Wiz MCP Server.

This module provides the tool definitions for the Wiz MCP Server, which enables
dynamic creation of tools based on these defintions.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Type

from wiz_mcp_server.utils.logger import get_logger

logger = get_logger()


@dataclass
class ToolParameter:
    """Definition of a parameter for a tool."""
    name: str
    type: Type
    description: str
    default: Any = None
    required: bool = False


@dataclass
class ToolDefinition:
    """Definition of a tool for the Wiz MCP Server."""
    name: str
    description: str
    graphql_query: str
    parameters: List[ToolParameter] = field(default_factory=list)
    variable_mapping: Dict[str, Any] = field(default_factory=dict)
    default_variables: Dict[str, Any] = field(default_factory=dict)
    disabled: bool = False

    def get_function_name(self) -> str:
        """Get the function name for the tool."""
        return f"wiz_{self.name.lower().replace(' ', '_')}"

    def prepare_variables(self, bound_args: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare variables for the GraphQL query.

        Supports:
        - Direct mappings: `cursor: after` → `variables['after'] = cursor_value`
        - Nested paths: `severity: {path: filterBy.severity}` → `variables['filterBy']['severity'] = value`
        - Deep nested paths: `updated_after: {path: filterBy.updatedAt.after}`

        Examples: `first: first`, `cursor: after`, `severity: {path: filterBy.severity}`
        """
        variables = self.default_variables.copy()

        for param_name, param_value in bound_args.items():
            if param_value is None:
                continue

            mapping = self.variable_mapping.get(param_name, param_name)

            # Direct mapping (e.g., cursor: after)
            if isinstance(mapping, str):
                variables[mapping] = param_value
                continue

            # Path mapping (e.g., {path: filterBy.severity})
            if isinstance(mapping, dict) and 'path' in mapping:
                path = mapping['path']

                # Handle paths with dots (nested paths)
                if '.' in path:
                    parts = path.split('.')

                    # Build the nested structure
                    current = variables
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]

                    # Set the value at the deepest level
                    current[parts[-1]] = param_value
                # Simple path without dots
                else:
                    variables[path] = param_value

        return variables
