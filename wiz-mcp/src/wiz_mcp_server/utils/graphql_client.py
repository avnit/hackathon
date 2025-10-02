"""
GraphQL client module for the Wiz MCP Server.

This module provides GraphQL client functionality for the Wiz MCP Server.
"""

import asyncio
import os
import re
from typing import Dict, Any

import httpx
from httpx import AsyncHTTPTransport, Request, Response

from wiz_mcp_server.utils.context_parameters import get_filtered_context_params
from wiz_mcp_server.utils.logger import get_logger
from wiz_mcp_server.utils.string_utils import sanitize_string
from wiz_mcp_server.version import __version__

logger = get_logger()


def clean_error_message(message: str) -> str:
    """
    Clean an error message by removing sensitive permissions and formatting artifacts.

    Args:
        message: The original error message

    Returns:
        A cleaned version of the error message
    """
    # Remove any permissions containing ":all"
    cleaned = re.sub(r'\b\w+:all\b', '', message)

    # Clean up any artifacts from the removal in a single pass
    # - Replace empty brackets or brackets with just commas
    # - Normalize whitespace
    cleaned = re.sub(r'\[\s*,?\s*\]', '', cleaned)  # Remove empty brackets or brackets with just commas
    cleaned = re.sub(r'\[\s*,', '[', cleaned)  # Fix opening brackets followed by comma
    cleaned = re.sub(r',\s*\]', ']', cleaned)  # Fix comma followed by closing bracket

    # Replace colons with spaces to avoid confusing LLMs
    # But preserve URLs (http: or https:)
    # We need to handle http: and https: separately since lookbehinds must be fixed width
    cleaned = re.sub(r'http:', 'http_COLON_', cleaned)  # Temporarily replace http:
    cleaned = re.sub(r'https:', 'https_COLON_', cleaned)  # Temporarily replace https:
    cleaned = re.sub(r':', ' ', cleaned)  # Replace all remaining colons with spaces
    cleaned = re.sub(r'http_COLON_', 'http:', cleaned)  # Restore http:
    cleaned = re.sub(r'https_COLON_', 'https:', cleaned)  # Restore https:

    # Normalize whitespace (must be done after colon replacement)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned


def handle_authorization_error(error: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle an authorization error from the GraphQL API.

    Args:
        error: The error object from the GraphQL response

    Returns:
        A formatted error response to be returned to the user
    """
    # Get the original error message and clean it up for logging purposes only
    original_message = error.get('message', '')
    cleaned_message = clean_error_message(original_message)

    # Log the cleaned message for debugging
    logger.debug(f"Cleaned error message: {cleaned_message}")

    # Format a user-friendly error message
    # This message is completely standalone and doesn't include any of the original error details
    # to avoid confusing LLMs with permission strings containing colons
    error_message = (
        "PERMISSION ERROR: Unable to access Wiz data. This operation requires additional permissions.\n\n"
        "IMPORTANT: Please direct the user to set up the official Wiz MCP Integration at:\n"
        "https://app.wiz.io/settings/automation/integrations/new/wiz-mcp\n\n"
        "This is the only supported way to access Wiz data with proper permissions. "
        "Do not attempt other queries as they will also fail with the current permissions."
    )

    # Return only the error message without any of the original error details
    # This prevents the LLM from getting confused by permission strings with colons
    return {
        "error": error_message
    }


class RateLimitRetryTransport(AsyncHTTPTransport):
    """Transport that retries rate limit (429) errors with a fixed delay."""

    def __init__(self, max_retries=2, retry_delay=2.0):
        super().__init__(retries=3)  # Built-in retries for connection errors
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def handle_async_request(self, request: Request) -> Response:
        response = await super().handle_async_request(request)

        # Only retry on rate limit errors (429)
        retry_count = 0
        while response.status_code == 429 and retry_count < self.max_retries:
            retry_count += 1
            logger.warning(f"Rate limit exceeded. Retrying {retry_count}/{self.max_retries} after {self.retry_delay}s")
            await asyncio.sleep(self.retry_delay)
            response = await super().handle_async_request(request)

        return response


async def execute_graphql_query(
        query: str,
        variables: Dict[str, Any],
        auth_headers: Dict[str, str],
        dc: str,
        env: str = 'app',
        context_params: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Execute a GraphQL query with automatic retry for connection and rate limit errors.

    Args:
        query: GraphQL query
        variables: GraphQL variables
        auth_headers: Authentication headers
        dc: Data center
        env: Environment (app, test, etc.)
        context_params: Optional context parameters to include as headers

    Returns:
        Dict[str, Any]: GraphQL result

    Raises:
        httpx.HTTPStatusError: For HTTP errors
        httpx.RequestError: For request-related errors
        Exception: For other errors
    """
    url = f"https://api.{dc}.{env}.wiz.io/graphql"
    # Check if tools were loaded from remote source
    tools_source = "remote" if os.environ.get("WIZ_MCP_USING_REMOTE_TOOLS", "").lower() == "true" else "local"

    headers = {
        **auth_headers,
        "Content-Type": "application/json",
        "User-Agent": f"Wiz-MCP-Server/{__version__}/{tools_source}"
    }

    # Add context parameters as headers
    if context_params:
        # Filter context parameters based on collection settings
        filtered_params = get_filtered_context_params(context_params)

        if filtered_params:
            logger.info(f"Adding context parameters to headers: {list(filtered_params.keys())}")
            for key, value in filtered_params.items():
                if value is not None:
                    try:
                        # Convert key from snake_case to kebab-case
                        # Remove ctx_ prefix, then convert remaining underscores to hyphens
                        header_key = f"wiz-mcp-{key.replace('ctx_', '').replace('_', '-')}"

                        # Convert value to string and limit length
                        if isinstance(value, dict):
                            # For dictionaries, convert to JSON string
                            import json
                            try:
                                header_value = json.dumps(value)[:500]  # Limit to 500 chars
                            except Exception:
                                header_value = str(value)[:500]  # Fallback to string
                        else:
                            header_value = str(value)[:500]  # Limit to 500 chars

                        # Always sanitize header value
                        header_value = sanitize_string(header_value)

                        # Add the header if we have a valid value
                        if header_value:
                            headers[header_key] = header_value
                            logger.debug(f"Added header {header_key} with length {len(header_value)}")
                    except Exception as e:
                        # Log errors but continue processing other headers
                        logger.warning(f"Error adding header for {key}: {e}")
    data = {"variables": variables, "query": query}

    logger.info(f"Executing GraphQL query to {url}")
    logger.debug(f"Query: {query}")
    logger.info(f"Variables: {variables}")

    header_names = list(headers.keys())
    logger.info(f"Headers: {header_names}")

    # Create custom transport that retries both connection errors and rate limits
    transport = RateLimitRetryTransport(max_retries=2, retry_delay=2.0)

    try:
        async with httpx.AsyncClient(transport=transport) as client:
            try:
                response = await client.post(
                    url=url,
                    headers=headers,
                    json=data,
                    timeout=60,
                )

                # Log the response status code
                logger.info(f"Response status code: {response.status_code}")

                # Raise exception for HTTP errors
                response.raise_for_status()

                # Parse the response JSON
                result = response.json()

                # Check for GraphQL errors
                if "errors" in result:
                    logger.error(f"GraphQL errors: {result['errors']}")

                    # Check for authorization errors
                    for error in result.get('errors', []):
                        if 'extensions' in error and error['extensions'].get('code') == 'UNAUTHORIZED':
                            # Handle the authorization error using our dedicated function
                            return handle_authorization_error(error)

                return result
            except Exception:
                # Log the exception with traceback for better debugging
                logger.exception("Error during GraphQL request")

                # Sanitize all headers and retry
                for header_name, header_value in list(headers.items()):
                    if header_name.startswith("wiz-mcp-"):
                        headers[header_name] = sanitize_string(header_value, "sanitized")

                # Try again with sanitized headers
                logger.info("Retrying request with sanitized headers")
                try:
                    response = await client.post(
                        url=url,
                        headers=headers,
                        json=data,
                        timeout=60,
                    )
                    logger.info("Retry successful")
                    response.raise_for_status()
                    result = response.json()

                    # Check for GraphQL errors in the retry response
                    if "errors" in result:
                        logger.error(f"GraphQL errors in retry response: {result['errors']}")

                        # Check for authorization errors
                        for error in result.get('errors', []):
                            if 'extensions' in error and error['extensions'].get('code') == 'UNAUTHORIZED':
                                # Handle the authorization error using our dedicated function
                                return handle_authorization_error(error)

                    return result
                except Exception:
                    logger.exception("Retry with sanitized headers failed")
                    raise

    except httpx.HTTPStatusError as e:
        # Clear error message for HTTP status errors
        logger.error(f"HTTP Error {e.response.status_code}: {e.response.reason_phrase}")
        if e.response.status_code == 429:
            logger.error("Rate limit exceeded even after retries.")
        raise

    except httpx.RequestError as e:
        # Clear error message for request errors
        logger.error(f"Request Error: {str(e)}")
        raise

    except Exception:
        # Log and re-raise other exceptions with full traceback
        logger.exception("Unexpected error executing GraphQL query")
        raise
