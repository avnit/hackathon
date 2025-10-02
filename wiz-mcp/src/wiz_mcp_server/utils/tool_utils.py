"""
Tool utilities for the Wiz MCP Server.

This module provides utility functions for working with tool definitions.
"""

from typing import Dict, Any, List, Type

from wiz_mcp_server.utils.logger import get_logger

logger = get_logger()


def get_type_from_string(type_str: str) -> Type:
    """
    Convert a type string to a Python type.

    Args:
        type_str: Type string (e.g., 'string', 'integer', 'array[string]')

    Returns:
        Python type
    """
    if type_str == 'string':
        return str
    elif type_str == 'integer':
        return int
    elif type_str == 'boolean':
        return bool
    elif type_str.startswith('array['):
        # Extract the item type
        item_type_str = type_str[6:-1]  # Remove 'array[' and ']'
        item_type = get_type_from_string(item_type_str)
        return List[item_type]
    elif type_str == 'object':
        return Dict[str, Any]
    else:
        # Default to string
        return str
