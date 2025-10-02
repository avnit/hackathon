# Testing Output Transformation

This guide explains how to test the new output transformation feature.

## Prerequisites

- A working Wiz MCP Server installation
- Valid Wiz API credentials

## Testing Steps

1. **Test with the default output transformation**

   Execute the `execute_wiz_query` tool with a simple query:

   ```bash
   # Create a simple payload file
   cat > test_output.yaml << EOF
   query:
     type: "VM"
   limit: 5
   project_id: "*"
   # Note: compact_mode has been replaced by output_transformation
   fetch_total_count: true
   EOF

   # Execute the tool
   WIZ_DOTENV_PATH=/path/to/your/.env python src/wiz_mcp_server/server.py --execute-tool execute_wiz_query --payload test_output.yaml
   ```

   Verify that the result is transformed according to the default configuration in `execute_wiz_query.yaml`.

2. **Test with a custom output transformation override**

   Use the example output transformation file:

   ```bash
   # Execute the tool with the custom output transformation
   WIZ_DOTENV_PATH=/path/to/your/.env python src/wiz_mcp_server/server.py --execute-tool execute_wiz_query --payload examples/output_transformation.yaml
   ```

   Verify that the result includes the additional fields specified in the output transformation override.

3. **Test different transformation options**

   Edit the `examples/output_transformation.yaml` file to test different options:

   ```yaml
   # Test keep_only_fields
   output_transformation:
     keep_only_fields:
       - graphSearch.totalCount
       - graphSearch.nodes.entities.id
       - graphSearch.nodes.entities.name
   ```

   ```yaml
   # Test remove_fields
   output_transformation:
     remove_fields:
       - graphSearch.nodes.entities.properties.tags
       - graphSearch.nodes.entities.technologies
   ```

   ```yaml
   # Test using both keep_only_fields and remove_fields together
   output_transformation:
     keep_only_fields:
       - graphSearch.totalCount
       - graphSearch.nodes.entities.id
       - graphSearch.nodes.entities.name
       - graphSearch.nodes.entities.properties
     remove_fields:
       - graphSearch.nodes.entities.properties.tags
   ```

   ```yaml
   # Test field-specific array limits
   output_transformation:
     field_array_limits:
       "graphSearch.nodes": 3
       "graphSearch.nodes.entities.technologies": 2
   ```

   ```yaml
   # Test field-specific text limits
   output_transformation:
     field_text_limits:
       "graphSearch.nodes.entities.properties.description": 30
   ```

   ```yaml
   # Test global array size limiting
   output_transformation:
     max_array_size: 5
   ```

   ```yaml
   # Test global text length limiting
   output_transformation:
     max_text_length: 50
   ```

   ```yaml
   # Test boolean field extraction
   output_transformation:
     keep_only_boolean_paths:
       - securityControls
       - tags
   ```

   Execute the tool with each configuration and verify that the result is transformed as expected.

4. **Test with the MCP Inspector**

   Start the MCP Inspector and test the `execute_wiz_query` tool with different output transformation configurations:

   ```bash
   WIZ_DOTENV_PATH=/path/to/your/.env uv run mcp dev src/wiz_mcp_server/server.py
   ```

   In the MCP Inspector:
   - Select the `execute_wiz_query` tool
   - Enter a simple query like `{ "type": "VM" }`
   - Set `limit` to 5
   # Note: compact_mode has been replaced by output_transformation
   - Add an `output_transformation` parameter with different configurations

## Expected Results

For each test, you should see:

1. The raw GraphQL result is transformed according to the specified configuration
2. Only the specified fields are included in the result (for keep_only_fields)
3. The specified fields are excluded from the result (for remove_fields)
4. Arrays are limited to the specified size (for max_array_size and field_array_limits)
5. Text fields are limited to the specified length (for max_text_length and field_text_limits)
6. Boolean fields are extracted from the specified paths (for keep_only_boolean_paths)
7. Debug information is preserved in the result

## Troubleshooting

If you encounter issues:

1. Check the logs for any error messages
2. Verify that the output transformation configuration is valid
3. Try with a simpler query or transformation configuration
4. Enable debug logging with `export WIZ_LOG_LEVEL=DEBUG`
