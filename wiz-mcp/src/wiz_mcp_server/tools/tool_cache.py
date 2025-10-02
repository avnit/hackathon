"""
Tool Cache for the Wiz MCP Server.

This module provides a cache for tool definitions to avoid loading them multiple times.
"""

from typing import List, Optional, Dict

from .tool_definition_classes import ToolDefinition

# Global cache for tool definitions
_tool_definitions_cache: Optional[List[ToolDefinition]] = None
_tool_definition_lookup_cache: Dict[str, Optional[ToolDefinition]] = {}
_cache_initialized = False


def get_cached_tool_definitions() -> Optional[List[ToolDefinition]]:
    """Get the cached tool definitions."""
    if _cache_initialized and _tool_definitions_cache is not None:
        return _tool_definitions_cache
    return None


def set_cached_tool_definitions(tools: List[ToolDefinition]) -> None:
    """Set the cached tool definitions."""
    global _tool_definitions_cache, _cache_initialized
    _tool_definitions_cache = tools
    _cache_initialized = True


def get_cached_tool_definition(tool_name: str) -> Optional[ToolDefinition]:
    """Get a cached tool definition by name."""
    return _tool_definition_lookup_cache.get(tool_name)


def set_cached_tool_definition(tool_name: str, tool_def: Optional[ToolDefinition]) -> None:
    """Set a cached tool definition by name."""
    _tool_definition_lookup_cache[tool_name] = tool_def
