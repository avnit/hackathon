"""
Authentication package for the Wiz MCP Server.

This package provides authentication functionality for the Wiz MCP Server.
"""

from .auth import authenticate, pad_base64

__all__ = ["authenticate", "pad_base64"]
