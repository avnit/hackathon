"""
Context module for the Wiz MCP Server.

This module provides the WizContext class for the Wiz MCP Server.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class WizContext:
    """Context for the Wiz MCP Server."""
    auth_headers: Dict[str, str]
    data_center: str
    env: str
