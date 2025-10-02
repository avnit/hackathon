"""
Example Tool for the Wiz MCP Server.

This module provides an example tool implementation for the Wiz MCP Server to help
developers understand how to create their own tools. This is a template that can be
used as a starting point for new tool development.
"""

from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP, Context

from wiz_mcp_server.utils.graphql_client import execute_graphql_query
from wiz_mcp_server.utils.logger import get_logger

logger = get_logger()


def register_example_tool(mcp: FastMCP) -> None:
    """
    Register the Example Tool with the FastMCP server.

    This function demonstrates how to register a tool with the FastMCP server.
    In a real implementation, you would replace this with your actual tool's
    registration function.

    Args:
        mcp: FastMCP server instance to register the tool with
    """

    @mcp.tool()
    async def get_wiz_example_data(
            param1: str,
            param2: Optional[int] = 10,
            param3: Optional[List[str]] = None,
            ctx: Context = None
    ) -> Dict[str, Any]:
        """
        Example tool function that demonstrates how to implement a Wiz MCP tool.

        This function shows the standard pattern for implementing a tool:
        1. Log the operation
        2. Get the Wiz context from the lifespan
        3. Process parameters and create filters
        4. Define the GraphQL query
        5. Execute the query and return the result

        Args:
            param1: A required string parameter (e.g., an ID or name)
            param2: An optional integer parameter with a default value
            param3: An optional list of strings

        Returns:
            Dict[str, Any]: The result of the GraphQL query
        """
        logger.info(f"Processing Example Tool request with param1: {param1}")

        # Get the Wiz context from the lifespan
        wiz_ctx = ctx.request_context.lifespan_context

        # Process parameters and create variables for the GraphQL query
        variables = {
            "requiredParam": param1,
            "optionalParam": param2,
        }

        # Add optional parameters if provided
        if param3:
            variables["listParam"] = param3

        # Define your GraphQL query
        # This is a placeholder query - replace with your actual query
        query = """
        query ExampleQuery($requiredParam: String!, $optionalParam: Int, $listParam: [String]) {
          # Replace this with your actual GraphQL query
          # This is just a placeholder to demonstrate the structure
          exampleData(
            id: $requiredParam,
            limit: $optionalParam,
            filters: $listParam
          ) {
            id
            name
            description
            createdAt
            # Add other fields you need
          }
        }
        """

        # Execute the GraphQL query
        result = await execute_graphql_query(
            query=query,
            variables=variables,
            auth_headers=wiz_ctx.auth_headers,
            dc=wiz_ctx.data_center,
            env=wiz_ctx.env
        )

        return result

# To use this tool, you would need to:
# 1. Import the registration function in server.py:
#    from wiz_mcp_server.tools.example_tool import register_example_tool
#
# 2. Register the tool in the get_server() function:
#    register_example_tool(mcp)
