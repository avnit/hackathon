"""
Wiz Search Tool for the Wiz MCP Server.

This module provides a combined tool that takes the output of text_to_wiz_query
and feeds it into execute_wiz_query, providing a seamless experience for users.
"""

import datetime
import json
import os
from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP, Context

from wiz_mcp_server.tools.fetch_tools import fetch_tools
from wiz_mcp_server.tools.load_definitions import load_tool_definition
from wiz_mcp_server.tools.tool_cache import get_cached_tool_definition, set_cached_tool_definition
from wiz_mcp_server.tools.tool_definition_classes import ToolDefinition
from wiz_mcp_server.utils.context_parameters import get_context_parameter_descriptions
from wiz_mcp_server.utils.graphql_client import execute_graphql_query
from wiz_mcp_server.utils.logger import get_logger

# Logger
logger = get_logger()


def find_tool_definition(tool_name: str) -> Optional[ToolDefinition]:
    """
    Find a tool definition by name.

    Args:
        tool_name: Name of the tool to find

    Returns:
        ToolDefinition or None if not found
    """
    # Check if we have this tool definition in the cache
    cached_tool = get_cached_tool_definition(tool_name)
    if cached_tool is not None:
        logger.info(f"Using cached tool definition for {tool_name}")
        return cached_tool

    # First, try to find the tool definition from the same source as other tools
    # Get all tool definitions
    tool_definitions = fetch_tools()

    # Look for the tool by name
    for tool_def in tool_definitions:
        if tool_def.name == tool_name:
            # Cache the tool definition for future lookups
            set_cached_tool_definition(tool_name, tool_def)
            return tool_def

    # If not found, fall back to the old method (direct file lookup)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    tool_defs_dir = os.path.join(current_dir, 'tool_definitions')
    yaml_path = os.path.join(tool_defs_dir, f"{tool_name}.yaml")

    if os.path.exists(yaml_path):
        tool_def = load_tool_definition(yaml_path)
        if tool_def:
            # Cache the tool definition for future lookups
            set_cached_tool_definition(tool_name, tool_def)
        return tool_def

    # Cache the fact that this tool definition doesn't exist
    set_cached_tool_definition(tool_name, None)
    return None


async def execute_tool_with_definition(tool_def: ToolDefinition, args: Dict[str, Any], ctx: Context,
                                       context_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute a GraphQL query using a tool definition.

    Args:
        tool_def: Tool definition to use
        args: Arguments to pass to the query
        ctx: MCP context
        context_params: Optional context parameters to include as headers

    Returns:
        Dict[str, Any]: The result of the GraphQL query
    """
    wiz_ctx = ctx.request_context.lifespan_context

    # Prepare variables for the GraphQL query
    variables = tool_def.prepare_variables(args)

    # Log the GraphQL query and variables for debugging
    logger.info(f"Executing GraphQL query for {tool_def.name}:")
    logger.info(f"Query: {tool_def.graphql_query}")
    logger.info(f"Variables: {variables}")

    # Execute the GraphQL query
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
        # Return the error message directly to the user
        return result

    # Add debug information to the result
    if isinstance(result, dict):
        result["_debug_variables"] = variables
        result["_debug_query"] = tool_def.graphql_query
        result["_debug_tool_name"] = tool_def.name

    return result


async def create_context_params(ctx_original_prompt: str, ctx_model_id: str, ctx_execution_environment: str) \
        -> Dict[str, str]:
    """
    Create context parameters dictionary for GraphQL requests.

    Args:
        ctx_original_prompt: The original prompt from the user
        ctx_model_id: The model ID
        ctx_execution_environment: The execution environment

    Returns:
        Dictionary of context parameters
    """
    return {
        "ctx_original_prompt": ctx_original_prompt,
        "ctx_model_id": ctx_model_id,
        "ctx_execution_environment": ctx_execution_environment,
        "ctx_tool_name": "wiz_search"  # Always use wiz_search as the tool name
    }


async def convert_natural_language_to_graph_query(query: str, ctx: Context, context_params: Dict[str, str]) \
        -> Dict[str, Any]:
    """
    Convert natural language to a Wiz Graph Query.

    Args:
        query: Natural language query
        ctx: MCP context
        context_params: Context parameters for GraphQL request

    Returns:
        Dictionary containing the graph query or error information
    """
    # Find the tool definition
    text_to_wiz_query_def = find_tool_definition("text_to_wiz_query")
    if not text_to_wiz_query_def:
        logger.error("Could not find text_to_wiz_query tool definition")
        return {
            "error": "Could not find text_to_wiz_query tool definition",
            "success": False
        }

    # Execute the tool
    nl_result = await execute_tool_with_definition(
        tool_def=text_to_wiz_query_def,
        args={"query": query},
        ctx=ctx,
        context_params=context_params
    )

    # Check for errors
    if "errors" in nl_result:
        logger.error(f"Error in text_to_wiz_query: {nl_result['errors']}")
        return {
            "error": "Failed to convert natural language to Wiz Graph Query",
            "details": nl_result,
            "success": False
        }

    # Extract the graph query JSON
    try:
        graph_query_json = nl_result.get("data", {}).get("aiGraphQuery", {}).get("aiGraphQueryResult", {}).get(
            "graphQueryJson")
        if not graph_query_json:
            logger.error("No graph query JSON found in the result")
            return {
                "error": "No graph query JSON found in the result",
                "details": nl_result,
                "success": False
            }

        # Handle the case where graphQueryJson is already a dictionary
        if isinstance(graph_query_json, dict):
            graph_query = graph_query_json
        else:
            # Parse the graph query JSON if it's a string
            graph_query = json.loads(graph_query_json)

        logger.info("Successfully converted natural language to Wiz Graph Query")
        logger.info(f"Graph query: {json.dumps(graph_query)}")

        return {
            "graph_query": graph_query,
            "success": True
        }

    except Exception as e:
        logger.error(f"Error parsing graph query JSON: {e}")
        return {
            "error": f"Error parsing graph query JSON: {e}",
            "details": nl_result,
            "success": False
        }


async def execute_graph_query(graph_query: Dict[str, Any], limit: int, project_id: str, fetch_total_count: bool,
                              output_transformation: Optional[Dict[str, Any]], after: Optional[str],
                              ctx: Context, context_params: Dict[str, str]) -> Dict[str, Any]:
    """
    Execute a Wiz Graph Query.

    Args:
        graph_query: The graph query to execute
        limit: Maximum number of results to return
        project_id: Project ID to scope the query to
        fetch_total_count: Whether to fetch the total count of results
        output_transformation: Optional configuration for transforming the output
        after: Pagination cursor for fetching the next page of results
        ctx: MCP context
        context_params: Context parameters for GraphQL request

    Returns:
        Dictionary containing the query result or error information
    """
    # Find the tool definition
    execute_wiz_query_def = find_tool_definition("execute_wiz_query")
    if not execute_wiz_query_def:
        logger.error("Could not find execute_wiz_query tool definition")
        return {
            "error": "Could not find execute_wiz_query tool definition",
            "success": False
        }

    # Prepare query arguments
    query_args = {
        "query": graph_query,
        "limit": limit,
        "project_id": project_id,
        "fetch_total_count": fetch_total_count,
        "output_transformation": output_transformation
    }

    # Add pagination parameters if needed
    is_paginating = after is not None
    if is_paginating:
        query_args["cursor"] = after
        # Set quick=false when paginating, as pagination is not supported in quick mode
        query_args["quick"] = False
        logger.info(f"Adding pagination cursor to query: {after} and setting quick=false")

    # Execute the query
    query_result = await execute_tool_with_definition(
        tool_def=execute_wiz_query_def,
        args=query_args,
        ctx=ctx,
        context_params=context_params
    )

    return query_result


async def wiz_search(
        query: str = None,
        limit: Optional[int] = 10,
        project_id: Optional[str] = "*",
        fetch_total_count: Optional[bool] = True,
        output_transformation: Optional[Dict[str, Any]] = None,
        after: Optional[str] = None,
        generated_query: Optional[Dict[str, Any]] = None,
        ctx_original_prompt: Optional[str] = None,
        ctx_model_id: Optional[str] = None,
        ctx_execution_environment: Optional[str] = None,
        ctx: Context = None
) -> Dict[str, Any]:
    """
    Convert natural language to a Wiz Graph Query and execute it. This is the primary tool for most queries about your
    cloud environment, resources, vulnerabilities, and configurations. Use this tool FIRST for questions about your
    environment such as finding resources, identifying vulnerabilities, checking exposures, or querying configurations.
    While this tool can find vulnerable resources and security concerns, it cannot retrieve the specific Wiz Issues or
    Wiz Threat Detection objects - use the dedicated tools for those specific cases. Examples: "Find vulnerable
    application endpoints", "Show exposed databases", "List VMs with critical vulnerabilities", "Check for insecure
    configurations".
    When users ask for counts (e.g., "how many VMs do I have"), set fetch_total_count=true and report the totalCount
    value from the response. If maxCountReached=true, inform the user that the count is the maximum limit (10,000) and
    the actual count may be higher.

    PAGINATION INSTRUCTIONS: When the response contains hasNextPage=true and the user wants to see more results,
    use this same tool with the following parameters:
    1. Set 'after' parameter to the endCursor value from the previous response
    2. Set 'generated_query' parameter to the exact same generated_query object from the previous response
    3. Keep all other parameters the same as the original query

    Note: The tool automatically sets quick=false when paginating, as pagination is not supported in quick mode.

    Example pagination call: wiz_search(after="endCursor_value", generated_query={...previous query object...},
    limit=10, project_id="*", ...)

    Args:
        query: Natural language description of what you want to find in Wiz. Example: 'Show me all vulnerabilities on
        EC2 machines', 'How many VMs do I have?'. Not required when paginating with 'after' parameter.
        limit: Maximum number of results to return
        project_id: Project ID to scope the query to. Use '*' for all projects
        fetch_total_count: Fetch total count of results. MUST be set to True when users ask 'how many' or any
        count-related questions.
        output_transformation: Optional configuration for transforming the output. Can include field filtering, array
        size limiting, and text length limiting.
        after: Pagination cursor for fetching the next page of results. When provided, the 'generated_query' parameter
        must also be provided.
        generated_query: The Wiz Graph Query object from a previous wiz_search call. Required when using the 'after'
        parameter for pagination.
        ctx_original_prompt: {{ctx_original_prompt_desc}}
        ctx_model_id: {{ctx_model_id_desc}}
        ctx_execution_environment: {{ctx_execution_environment_desc}}
        ctx_tool_name: {{ctx_tool_name_desc}}
        ctx: MCP context

    NOTE: The ctx_* parameters above are REQUIRED for proper tool operation and debugging. You MUST provide values for
    all of them.

    Returns:
        Dict[str, Any]: The combined result with both the generated query and its execution results
    """
    # Check if we're paginating (after parameter is provided)
    is_paginating = after is not None

    # Validate parameters
    if is_paginating and generated_query is None:
        return {
            "error": "Missing required parameter",
            "details": "When using the 'after' parameter for pagination, you must also provide the 'generated_query' "
                       "parameter."
        }

    if not is_paginating and query is None:
        return {
            "error": "Missing required parameter",
            "details": "The 'query' parameter is required when not paginating with 'after'."
        }

    # Create context parameters
    context_params = await create_context_params(
        ctx_original_prompt=ctx_original_prompt,
        ctx_model_id=ctx_model_id,
        ctx_execution_environment=ctx_execution_environment
    )

    # Get the graph query
    if is_paginating:
        logger.info(f"Processing wiz_search pagination request with cursor: {after}")
        # Use the provided generated_query directly
        graph_query = generated_query
    else:
        logger.info(f"Processing wiz_search query: {query}")
        # Convert natural language to graph query
        result = await convert_natural_language_to_graph_query(query, ctx, context_params)
        if not result.get("success"):
            # Return the error if conversion failed
            return {k: v for k, v in result.items() if k != "success"}
        graph_query = result.get("graph_query")

    # Execute the graph query
    query_result = await execute_graph_query(
        graph_query=graph_query,
        limit=limit,
        project_id=project_id,
        fetch_total_count=fetch_total_count,
        output_transformation=output_transformation,
        after=after,
        ctx=ctx,
        context_params=context_params
    )

    # Combine the results
    combined_result = {
        "generated_query": graph_query,
        "query_results": query_result,
        "_context": {
            "original_prompt": ctx_original_prompt,
            "model_id": ctx_model_id,
            "execution_environment": ctx_execution_environment
        }
    }

    # Add the original query if we're not paginating
    if not is_paginating:
        combined_result["original_natural_language_query"] = query

    # Apply output transformation if provided
    if output_transformation:
        from wiz_mcp_server.utils.output_transform import transform_output
        logger.info("Applying output transformation to wiz_search result")
        combined_result = transform_output(combined_result, output_transformation)

    return combined_result


def prepare_tool_description() -> str:
    """
    Prepare the description for the wiz_search tool.

    Returns:
        Formatted description string
    """
    # Get the description from the wiz_search function
    description = wiz_search.__doc__.strip()

    # Get context parameter descriptions
    context_param_descriptions = get_context_parameter_descriptions()

    # Replace placeholders in the description with actual descriptions
    description = description.replace("{{ctx_original_prompt_desc}}",
                                      context_param_descriptions["ctx_original_prompt"])
    description = description.replace("{{ctx_model_id_desc}}", context_param_descriptions["ctx_model_id"])
    description = description.replace("{{ctx_execution_environment_desc}}",
                                      context_param_descriptions["ctx_execution_environment"])
    description = description.replace("{{ctx_tool_name_desc}}", context_param_descriptions["ctx_tool_name"])

    # Add source and timestamp to the description
    source = "Remote" if os.environ.get("WIZ_MCP_USING_REMOTE_TOOLS", "").lower() == "true" else "Local"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    description = f"{description} [{source}: {timestamp}]"

    return description


def register_wiz_search_tool(mcp: FastMCP) -> None:
    """
    Register the wiz_search tool with the FastMCP server.

    This function registers a tool that chains text_to_wiz_query and execute_wiz_query.
    Note: This tool is implemented directly in code and does not rely on a YAML definition.

    Args:
        mcp: FastMCP server instance to register the tool with
    """
    # Find the tool definitions to get their descriptions
    text_to_wiz_query_def = find_tool_definition("text_to_wiz_query")
    execute_wiz_query_def = find_tool_definition("execute_wiz_query")

    if not text_to_wiz_query_def or not execute_wiz_query_def:
        logger.warning("Could not find required tool definitions, but will still register wiz_search tool")

    # Prepare the tool description
    description = prepare_tool_description()

    # Register the tool with explicit description
    @mcp.tool(name="wiz_search", description=description)
    async def wiz_search_tool(
            query: str = None,
            limit: Optional[int] = 10,
            project_id: Optional[str] = "*",
            fetch_total_count: Optional[bool] = True,
            output_transformation: Optional[Dict[str, Any]] = None,
            after: Optional[str] = None,
            generated_query: Optional[Dict[str, Any]] = None,
            ctx_original_prompt: Optional[str] = None,
            ctx_model_id: Optional[str] = None,
            ctx_execution_environment: Optional[str] = None,
            ctx: Context = None
    ) -> Dict[str, Any]:
        return await wiz_search(
            query=query,
            limit=limit,
            project_id=project_id,
            fetch_total_count=fetch_total_count,
            output_transformation=output_transformation,
            after=after,
            generated_query=generated_query,
            ctx_original_prompt=ctx_original_prompt,
            ctx_model_id=ctx_model_id,
            ctx_execution_environment=ctx_execution_environment,
            ctx=ctx
        )

    logger.info("Registered wiz_search tool")
