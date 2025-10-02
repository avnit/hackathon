"""
Remote Tool Definition Loader.

This module provides functionality to load tool definitions from remote sources.
"""

import base64
import io
import os
import tempfile
import time
import urllib.request
import zipfile
from typing import Dict, List, Optional, Tuple

from wiz_mcp_server.utils.logger import get_logger
from .tool_definition_classes import ToolDefinition
from .tool_definition_loader import ToolDefinitionLoader
from .tool_definition_utils import parse_yaml_to_tool_definition

logger = get_logger()

# Encrypted URL for remote tools
ENCRYPTED_REMOTE_TOOLS_URL = "XhcQSBIITRdaW0MIXwBER1cIRFpNEAYDWQtRTF8IAkNBHFIOW0wJWxEdFVFXH1QCQABAXVoIXhQPAkFISxIeTFkW"  # noqa: E501


def decrypt(encrypted_b64: str, key: str) -> str:
    """
    Decrypt a base64-encoded string using XOR with the provided key.

    Args:
        encrypted_b64: Base64-encoded encrypted string
        key: Decryption key

    Returns:
        str: Decrypted string
    """
    key_bytes = key.encode()
    encrypted = base64.b64decode(encrypted_b64)
    decrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted)])
    return decrypted.decode()


class RemoteToolDefinitionLoader(ToolDefinitionLoader):
    """Loader for tool definitions from remote sources (e.g., ZIP files, URLs)."""

    # Class-level cache for the downloaded zip content
    _zip_cache: Dict[str, Tuple[bytes, float]] = {}
    # Cache expiration time in seconds (5 minutes)
    CACHE_EXPIRATION = 300
    # Download timeout in seconds
    DOWNLOAD_TIMEOUT = 30

    def load_definition(self, source_identifier: str) -> Optional[ToolDefinition]:
        """
        Load a tool definition from a remote source.

        Args:
            source_identifier: Identifier for the remote source (e.g., path within ZIP file)

        Returns:
            ToolDefinition or None if the definition could not be loaded
        """
        try:
            # This method is called with a path within the extracted ZIP
            # The path should be a YAML file
            if not os.path.exists(source_identifier):
                logger.error(f"Tool definition file not found: {source_identifier}")
                return None

            with open(source_identifier, 'r') as f:
                yaml_content = f.read()

            return parse_yaml_to_tool_definition(yaml_content, source_identifier)

        except Exception as e:
            logger.error(f"Error loading tool definition from {source_identifier}: {e}")
            return None

    def _get_zip_content(self, source_location: str) -> Optional[bytes]:
        """
        Get the zip content from cache or download it if needed.

        Args:
            source_location: URL to download from

        Returns:
            Zip content as bytes or None if download failed
        """
        try:
            current_time = time.time()

            # Check if we have a valid cache entry
            if source_location in self._zip_cache:
                cached_content, cached_time = self._zip_cache[source_location]
                # Check if the cache is still valid (less than 5 minutes old)
                if current_time - cached_time < self.CACHE_EXPIRATION:
                    logger.info("Using cached tool definition")
                    return cached_content
                else:
                    age_min = (current_time - cached_time) / 60
                    logger.info(f"Cache expired after {age_min:.1f} minutes, downloading fresh copy")
            else:
                logger.info("No cached tool definitions found, downloading from remote source")

            # Download the zip file
            with urllib.request.urlopen(source_location, timeout=self.DOWNLOAD_TIMEOUT) as response:
                zip_content = response.read()

            # Update the cache
            self._zip_cache[source_location] = (zip_content, current_time)
            return zip_content

        except Exception as e:
            logger.error(f"Error downloading tool definitions from {source_location}: {e}")
            return None

    def load_all_definitions(self, source_location: str) -> List[ToolDefinition]:
        """
        Load all tool definitions from a remote source location.

        Args:
            source_location: Remote location containing tool definitions (e.g., ZIP URL)

        Returns:
            List of tool definitions
        """
        tool_defs = []

        try:
            # Get the zip content (from cache or download)
            zip_content = self._get_zip_content(source_location)
            if not zip_content:
                logger.error("Failed to get zip content, returning empty tool definitions list")
                return []

            # Create a temporary directory to extract files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract the ZIP file
                with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_ref:
                    zip_ref.extractall(temp_dir)

                    # Find the tool_definitions directory in the extracted ZIP
                    # The new structure has a single tool_definitions folder at the top level
                    tool_defs_dir = None

                    # Fall back to searching for the old structure
                    for root, _, _ in os.walk(temp_dir):
                        if os.path.basename(root) == 'tool_definitions':
                            tool_defs_dir = root
                            break

                    if not tool_defs_dir:
                        logger.error("Could not find tool_definitions directory in the ZIP file")
                        return []

                    # Get all YAML files in the directory
                    all_files = os.listdir(tool_defs_dir)
                    yaml_files = [f for f in all_files if f.endswith('.yaml')]

                    for yaml_file in yaml_files:
                        yaml_path = os.path.join(tool_defs_dir, yaml_file)

                        # Load the tool definition
                        tool_def = self.load_definition(yaml_path)
                        if tool_def:
                            tool_defs.append(tool_def)
        except Exception as e:
            logger.error(f"Error loading tool definitions from {source_location}: {e}")

        return tool_defs

    @classmethod
    def clear_cache(cls, source_location: Optional[str] = None) -> None:
        """
        Clear the zip content cache.

        Args:
            source_location: Optional URL to clear from cache. If None, clears the entire cache.
        """
        if source_location:
            if source_location in cls._zip_cache:
                del cls._zip_cache[source_location]
                logger.info(f"Cleared cache for {source_location}")
        else:
            cls._zip_cache.clear()
            logger.info("Cleared entire remote tools cache")

    @classmethod
    def get_cache_status(cls) -> Dict[str, Dict[str, str]]:
        """
        Get the status of the cache.

        Returns:
            Dict with cache information including URLs and age
        """
        current_time = time.time()
        status = {}

        for url, (_, timestamp) in cls._zip_cache.items():
            age_seconds = current_time - timestamp
            age_minutes = age_seconds / 60
            expires_in = max(0, cls.CACHE_EXPIRATION - age_seconds)

            status[url] = {
                "age": f"{age_minutes:.2f} minutes",
                "expires_in": f"{expires_in:.2f} seconds",
                "valid": age_seconds < cls.CACHE_EXPIRATION
            }

        return status
