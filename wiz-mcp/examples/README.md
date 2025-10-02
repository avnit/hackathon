# Wiz MCP Server Examples

This directory contains example payloads for testing Wiz MCP Server tools.

## Tool Payloads

These YAML files contain parameters for executing specific tools:

- `text_to_wiz_query_payload.yaml`: Convert natural language to a Wiz Graph Query
- `execute_wiz_query_payload.yaml`: Execute a Wiz Graph Query
- `execute_wiz_query_json_payload.yaml`: Execute a Wiz Graph Query with a JSON-formatted query
- `execute_wiz_query_compact_payload.yaml`: Execute a Wiz Graph Query with compact mode enabled
- `get_threats_payload.yaml`: Retrieve threat detection issues with detailed information
- `wiz_search_payload.yaml`: Combined tool that converts natural language to a Wiz Graph Query and executes it

## Tool Examples

The `tool_examples` directory contains examples of tool definitions and their corresponding payloads:

- `get_kubernetes_clusters.yaml`: A tool definition for retrieving Kubernetes clusters
- `get_kubernetes_clusters_payload.yaml`: A payload for testing the Kubernetes clusters tool

## Using the Examples

You can use these examples to test the Wiz MCP Server tools:

```bash
# Convert natural language to a Wiz Graph Query
WIZ_DOTENV_PATH=/path/to/your/.env uv run --with mcp[cli] python src/wiz_mcp_server/server.py --execute-tool text_to_wiz_query --payload examples/text_to_wiz_query_payload.yaml

# Execute a Wiz Graph Query
WIZ_DOTENV_PATH=/path/to/your/.env uv run --with mcp[cli] python src/wiz_mcp_server/server.py --execute-tool execute_wiz_query --payload examples/execute_wiz_query_payload.yaml

# Execute a Wiz Graph Query with compact mode
WIZ_DOTENV_PATH=/path/to/your/.env uv run --with mcp[cli] python src/wiz_mcp_server/server.py --execute-tool execute_wiz_query --payload examples/execute_wiz_query_compact_payload.yaml

# Retrieve threat detection issues
WIZ_DOTENV_PATH=/path/to/your/.env uv run --with mcp[cli] python src/wiz_mcp_server/server.py --execute-tool get_threats --payload examples/get_threats_payload.yaml

# Use the wiz_search tool
WIZ_DOTENV_PATH=/path/to/your/.env uv run --with mcp[cli] python src/wiz_mcp_server/server.py --execute-tool wiz_search --payload examples/wiz_search_payload.yaml

# Alternatively, you can run directly with Python
WIZ_DOTENV_PATH=/path/to/your/.env python src/wiz_mcp_server/server.py --execute-tool execute_wiz_query --payload examples/execute_wiz_query_payload.yaml
```

## Creating Your Own Tools

To create your own tool:

1. Copy a tool definition from `tool_examples` to `src/wiz_mcp_server/tools/tool_definitions/`
2. Create a payload file in the `examples` directory
3. Test your tool using the `--execute-tool` command

For detailed instructions, see the [Creating and Testing Custom Tools](../docs/creating_tools.md) guide.
