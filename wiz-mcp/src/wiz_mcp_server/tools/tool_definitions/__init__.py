"""
Tool Definitions package for the Wiz MCP Server.

This package contains YAML files that define tools for the Wiz MCP Server.
"""

# Re-export ToolDefinition and ToolParameter from the parent module
from ..tool_definition_classes import ToolDefinition, ToolParameter

__all__ = ["ToolDefinition", "ToolParameter"]
