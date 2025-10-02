"""
Dynamic Tools for the Wiz MCP Server.

This module provides the dynamic tool registration functionality for the Wiz MCP Server.
"""

import inspect
from typing import Dict, Any

from mcp.server.fastmcp import FastMCP, Context

from wiz_mcp_server.utils.context_parameters import get_context_parameters, get_context_parameter_descriptions
from wiz_mcp_server.utils.graphql_client import execute_graphql_query
from wiz_mcp_server.utils.output_transform import transform_output
from .fetch_tools import fetch_tools
from .tool_definition_classes import ToolDefinition
from ..utils.logger import get_logger

logger = get_logger()


def register_dynamic_tools(mcp: FastMCP) -> None:
    """
    Register dynamic tools with the FastMCP server.

    This function fetches tool definitions and dynamically registers them with the
    FastMCP server.

    Args:
        mcp: FastMCP server instance to register the tools with
    """
    # Fetch tool definitions
    # TODO: This will be replaced by fetching the tool definitions from the Wiz API directly.
    tool_definitions = fetch_tools()

    # Register each tool (skip disabled tools)
    for tool_def in tool_definitions:
        if tool_def.disabled:
            logger.info(f"Skipping disabled tool: {tool_def.name}")
            continue
        register_dynamic_tool(mcp, tool_def)


def create_tool_signature(tool_def: ToolDefinition) -> tuple[inspect.Signature, Dict[str, Any], str]:
    """
    Create a function signature from a tool definition.

    Args:
        tool_def: Tool definition to create signature from

    Returns:
        tuple containing:
        - inspect.Signature: The function signature
        - Dict[str, Any]: Parameter annotations
        - str: Function docstring
    """
    # Create parameter annotations and defaults
    param_annotations = {}
    param_defaults = {}

    # Add context parameter
    param_annotations["ctx"] = Context
    param_defaults["ctx"] = None

    # Add tool parameters
    for param in tool_def.parameters:
        param_annotations[param.name] = param.type
        if not param.required:
            param_defaults[param.name] = param.default

    # Add context parameters
    context_params = get_context_parameters()
    for param in context_params:
        param_name = param["name"]
        param_type = param["type"]
        param_default = param["default"]

        # Add to annotations and defaults
        from wiz_mcp_server.utils.tool_utils import get_type_from_string
        param_annotations[param_name] = get_type_from_string(param_type)
        param_defaults[param_name] = param_default

    # Create function signature
    # We need to ensure required parameters come before optional ones
    required_params = []
    optional_params = []

    # Process all parameters in a single loop
    for param in tool_def.parameters:
        # Set default based on whether parameter is required
        default = inspect.Parameter.empty if param.required else param_defaults.get(param.name, inspect.Parameter.empty)

        func_parameter = inspect.Parameter(
            name=param.name,
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=default,
            annotation=param_annotations.get(param.name, inspect.Parameter.empty)
        )

        # Add to appropriate list
        (required_params if param.required else optional_params).append(func_parameter)

    # Add context parameters
    context_parameters = []
    for param in get_context_parameters():
        param_name = param["name"]
        context_parameters.append(inspect.Parameter(
            name=param_name,
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=param_defaults.get(param_name),
            annotation=param_annotations.get(param_name)
        ))

    # Finally add the context parameter
    ctx_param = inspect.Parameter(
        name="ctx",
        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
        default=None,
        annotation=Context
    )

    # Combine all parameters in the correct order
    all_params = required_params + optional_params + context_parameters + [ctx_param]

    sig = inspect.Signature(
        parameters=all_params,
        return_annotation=Dict[str, Any]
    )

    # Create function docstring
    docstring = f"{tool_def.description}\n\nArgs:\n"
    for param in tool_def.parameters:
        default_str = f" (default: {param.default})" if not param.required else ""
        docstring += f"    {param.name}: {param.description}{default_str}\n"

    # Add context parameters to docstring with emphasis
    context_param_descriptions = get_context_parameter_descriptions()
    for param_name, description in context_param_descriptions.items():
        # Add extra emphasis for context parameters
        docstring += f"    {param_name}: {description}\n"

    # Add a special note about context parameters
    docstring += "\nNOTE: The ctx_* parameters above are REQUIRED for proper tool operation and debugging.\n"

    docstring += "\nReturns:\n    Dict[str, Any]: The result of the GraphQL query"

    return sig, param_annotations, docstring


def register_dynamic_tool(mcp: FastMCP, tool_def: ToolDefinition) -> None:
    """
    Register a dynamic tool with the FastMCP server.

    Args:
        mcp: FastMCP server instance to register the tool with
        tool_def: Tool definition to register
    """
    # Create the function signature and docstring
    sig, _, docstring = create_tool_signature(tool_def)  # Using _ to ignore unused param_annotations

    # Create the async function
    async def dynamic_tool(*args, **kwargs):
        # Bind arguments to parameters
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Get the context
        ctx = bound_args.arguments["ctx"]
        wiz_ctx = ctx.request_context.lifespan_context

        logger.info(f"Processing {tool_def.name} request")

        # Extract context parameters
        context_params = {
            # Add tool name to context parameters
            "ctx_tool_name": tool_def.name
        }

        for param in get_context_parameters():
            param_name = param["name"]
            if param_name in bound_args.arguments:
                # Store with shorter names in the result
                short_name = param_name.replace('ctx_', '')
                context_params[short_name] = bound_args.arguments[param_name]

        # Create variables for the GraphQL query
        args_without_ctx = {k: v for k, v in bound_args.arguments.items()
                            if k != "ctx" and not k.startswith("ctx_")}
        variables = tool_def.prepare_variables(args_without_ctx)

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
            context_params=context_params  # Will be filtered in execute_graphql_query
        )

        # Check if we received an error message from the GraphQL client
        if isinstance(result, dict) and "error" in result:
            logger.error(f"GraphQL error in {tool_def.name}: {result['error']}")
            # Return the error message directly to the user
            return result

        # Log the result for debugging
        if "errors" in result:
            logger.error(f"GraphQL errors: {result['errors']}")
        else:
            logger.info(f"GraphQL query for {tool_def.name} executed successfully")

        # Add debug information to the result
        if isinstance(result, dict):
            result["_debug_variables"] = variables
            result["_debug_query"] = tool_def.graphql_query
            result["_debug_tool_name"] = tool_def.name

            # Add context parameters to the result
            if context_params:
                result["_context"] = context_params

            # Apply output transformation if configured and not disabled
            if hasattr(tool_def, 'variable_mapping') and 'output_transformation' in tool_def.variable_mapping:
                output_transformation = tool_def.variable_mapping.get('output_transformation', {})
                if not output_transformation.get('disabled', False):
                    logger.info(f"Applying output transformation for {tool_def.name}")
                    result = transform_output(result, output_transformation)

        return result

    # Set function attributes
    dynamic_tool.__name__ = tool_def.get_function_name()
    dynamic_tool.__doc__ = docstring
    dynamic_tool.__signature__ = sig

    # Register the tool
    mcp.add_tool(dynamic_tool)

    logger.info(f"Registered dynamic tool: {tool_def.name}")
