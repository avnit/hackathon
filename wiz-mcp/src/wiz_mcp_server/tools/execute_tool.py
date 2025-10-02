"""
Tool Execution Module.

This module provides functionality to execute a tool directly without starting the MCP server.
"""

import json
import sys

import yaml

from wiz_mcp_server.tools.fetch_tools import fetch_tools
from wiz_mcp_server.utils.context import WizContext
from wiz_mcp_server.utils.graphql_client import execute_graphql_query
from wiz_mcp_server.utils.logger import get_logger
from wiz_mcp_server.utils.output_transform import transform_output

logger = get_logger()


async def execute_tool_directly(tool_name: str, payload_path: str) -> None:
    """Execute a specific tool directly. Use for testing only.

    Args:
        tool_name: Name of the tool to execute
        payload_path: Path to a YAML file containing the tool parameters
    """
    from dotenv import load_dotenv
    import os

    # Get the directory where agent.py is located
    AGENT_DIR = os.path.dirname(os.path.abspath(__file__)).split('wiz-mcp')[0]
    ENV_PATH = os.path.join(AGENT_DIR, ".env")
    load_dotenv(ENV_PATH)

    # Import here to avoid circular imports
    from wiz_mcp_server.auth.auth import authenticate

    # Authenticate with Wiz API
    auth_result = await authenticate()
    wiz_ctx = WizContext(
        auth_headers=auth_result.auth_headers,
        data_center=auth_result.data_center,
        env=auth_result.env
    )

    # Load all tool definitions
    tool_definitions = fetch_tools()

    # Import wiz_search for special handling
    if tool_name.lower() == "wiz_search":
        logger.info("Executing the wiz_search tool")
        # Import here to avoid circular imports
        from wiz_mcp_server.tools.wiz_search_tool import wiz_search

        # Create a mock context for the tool execution
        class MockRequestContext:
            def __init__(self, lifespan_context):
                self.lifespan_context = lifespan_context

        class MockContext:
            def __init__(self, request_context):
                self.request_context = request_context

        request_ctx = MockRequestContext(wiz_ctx)
        ctx = MockContext(request_ctx)

        # Use a minimal tool definition for logging
        from wiz_mcp_server.tools.tool_definition_classes import ToolDefinition
        tool_def = ToolDefinition(
            name="wiz_search",
            description="Convert natural language to a Wiz Graph Query and execute it. This is the primary tool for most"
                        " queries about your cloud environment, resources, vulnerabilities, and configurations.",
            graphql_query="# Placeholder"
        )
    else:
        # Find the requested tool in the standard way
        tool_def = None
        for td in tool_definitions:
            if td.name.lower() == tool_name.lower():
                tool_def = td
                break

        if not tool_def:
            logger.error(f"Tool '{tool_name}' not found")
            sys.exit(1)

    # Load the payload from YAML file
    try:
        with open(payload_path, 'r') as f:
            payload = yaml.safe_load(f)
            logger.info(f"Loaded payload from {payload_path}")
    except Exception as e:
        logger.error(f"Error loading payload from {payload_path}: {e}")
        sys.exit(1)

    # Parse any JSON strings in the payload
    for key, value in payload.items():
        if isinstance(value, str) and value.strip().startswith('{') and value.strip().endswith('}'):
            try:
                payload[key] = json.loads(value)
                logger.info(f"Parsed JSON string for parameter '{key}'")
            except json.JSONDecodeError:
                # If it's not valid JSON, keep it as a string
                pass

    # Prepare variables for the GraphQL query
    variables = tool_def.prepare_variables(payload)

    # Log the GraphQL query and variables
    logger.info(f"Executing GraphQL query for {tool_def.name}:")
    logger.info(f"Query: {tool_def.graphql_query}")
    logger.info(f"Variables: {json.dumps(variables, indent=2)}")

    # Extract context parameters if present
    context_params = {
        "ctx_original_prompt": payload.get("ctx_original_prompt"),
        "ctx_model_id": payload.get("ctx_model_id"),
        "ctx_execution_environment": payload.get("ctx_execution_environment"),
        "ctx_tool_name": tool_def.name  # Add tool name to context parameters
    }

    # Execute the tool
    if tool_name.lower() == "wiz_search":
        # Special handling for the wiz_search tool
        logger.info("Executing the wiz_search tool")

        result = {
            "data": await wiz_search(
                query=payload["query"],
                limit=payload.get("limit", 10),
                project_id=payload.get("project_id", "*"),
                output_transformation=payload.get("output_transformation"),
                fetch_total_count=payload.get("fetch_total_count", True),
                ctx_original_prompt=context_params["ctx_original_prompt"],
                ctx_model_id=context_params["ctx_model_id"],
                ctx_execution_environment=context_params["ctx_execution_environment"],
                ctx=ctx
            )
        }
    else:
        # Standard execution for regular tools
        result = await execute_graphql_query(
            query=tool_def.graphql_query,
            variables=variables,
            auth_headers=wiz_ctx.auth_headers,
            dc=wiz_ctx.data_center,
            env=wiz_ctx.env,
            context_params=context_params
        )

    # Check if we received an error message from the GraphQL client
    if isinstance(result, dict) and "error" in result:
        logger.error(f"GraphQL error in {tool_def.name}: {result['error']}")
        # Log the error message as JSON
        logger.error(f"Error details: {json.dumps(result, indent=2)}")
        return

    # Add debug information if not already added
    if tool_name.lower() != "wiz_search" and result.get('data'):
        result['data']['_debug_variables'] = variables
        result['data']['_debug_query'] = tool_def.graphql_query
        result['data']['_debug_tool_name'] = tool_def.name

    # Apply output transformation if needed
    if tool_name.lower() != "wiz_search" and result.get('data'):
        # Check if we have a transformation configuration in the tool definition
        transformation_config = None

        # Check for output_transformation in tool definition
        if tool_def and hasattr(tool_def, 'variable_mapping') and 'output_transformation' in tool_def.variable_mapping:
            transformation_config = tool_def.variable_mapping['output_transformation'].copy()

        # Check for override in payload
        if transformation_config and 'output_transformation' in payload:
            # Merge the override with the base configuration
            override = payload['output_transformation']
            transformation_config.update(override)
        elif 'output_transformation' in payload:
            # If no configuration in tool definition, use payload directly
            transformation_config = payload['output_transformation']

        # Apply the transformation if we have a configuration
        if transformation_config:
            logger.info("Applying output transformation to result")
            result['data'] = transform_output(result['data'], transformation_config)

    # Log the result as JSON
    logger.info(f"Tool execution result: {json.dumps(result, indent=2)}")
