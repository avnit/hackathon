"""
Authentication module for the Wiz MCP Server.

This module provides authentication functionality for the Wiz MCP Server.
"""

import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

from wiz_mcp_server.utils.logger import get_logger

logger = get_logger()


@dataclass
class AuthResult:
    """Result of authentication with the Wiz API."""
    auth_headers: Dict[str, str]
    data_center: str
    env: str


# Global variables for token caching
_access_token: Optional[str] = None
_token_expiry: Optional[float] = None
_data_center: Optional[str] = None


def reset_auth_cache() -> None:
    """Reset the authentication cache."""
    global _access_token, _token_expiry, _data_center
    _access_token = None
    _token_expiry = None
    _data_center = None


def pad_base64(base64_str: str) -> str:
    """
    Pad a base64 string to a multiple of 4.

    Args:
        base64_str: Base64 string to pad

    Returns:
        str: Padded base64 string
    """
    remainder = len(base64_str) % 4
    if remainder == 0:
        return base64_str
    return base64_str + "=" * (4 - remainder)


async def authenticate() -> AuthResult:
    """
    Authenticate with the Wiz API.

    Returns:
        AuthResult: Authentication result containing headers, data center and environment

    Raises:
        ValueError: If WIZ_CLIENT_ID or WIZ_CLIENT_SECRET environment variables are not set
    """
    global _access_token, _token_expiry, _data_center

    # Check if we have a valid cached token
    current_time = time.time()
    env = os.environ.get("WIZ_ENV", "app")
    if _access_token and _token_expiry and _data_center and current_time < _token_expiry:
        logger.debug("Using cached access token")
        return AuthResult(
            auth_headers={"Authorization": f"Bearer {_access_token}"},
            data_center=_data_center,
            env=env
        )

    # Get client ID and secret from environment variables
    client_id = os.environ.get("WIZ_CLIENT_ID")
    client_secret = os.environ.get("WIZ_CLIENT_SECRET")
    env = os.environ.get("WIZ_ENV", "app")

    # Explicitly check for missing environment variables
    if client_id is None or client_secret is None:
        # Reset cached values to ensure tests work correctly
        reset_auth_cache()
        raise ValueError("WIZ_CLIENT_ID and WIZ_CLIENT_SECRET environment variables must be set")

    # Authenticate with the Wiz API
    logger.info("Authenticating with the Wiz API")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=f"https://auth.{env}.wiz.io/oauth/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "audience": "wiz-api",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=60,
        )

        response.raise_for_status()
        auth_data = response.json()

        # Extract the access token and expiry time
        _access_token = auth_data["access_token"]
        _token_expiry = time.time() + auth_data["expires_in"] - 60  # Subtract 60 seconds for safety

        # Extract the data center from the JWT token
        token_parts = _access_token.split(".")
        if len(token_parts) >= 2:
            # Decode the JWT payload
            payload = token_parts[1]
            padded_payload = pad_base64(payload)
            decoded_payload = base64.b64decode(padded_payload)
            payload_data = json.loads(decoded_payload)

            # Extract the data center
            _data_center = payload_data.get("dc", "us1")

            # Try to extract the affiliation_id for remote tools key
            try:
                affiliation_id = json.loads(payload_data.get('integration', "{}")).get('affiliation_id', "")
                if affiliation_id:
                    os.environ["WIZ_MCP_REMOTE_TOOLS_KEY"] = affiliation_id
                    logger.debug("Set WIZ_MCP_REMOTE_TOOLS_KEY from JWT token")
            except Exception as e:
                logger.debug(f"Could not extract affiliation_id from JWT token: {e}")
        else:
            _data_center = "us1"

        logger.info(f"Successfully authenticated with the Wiz API (DC: {_data_center})")

        return AuthResult(
            auth_headers={"Authorization": f"Bearer {_access_token}"},
            data_center=_data_center,
            env=env
        )
