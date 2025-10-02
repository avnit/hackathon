# Output Transformation

The Wiz MCP Server supports configurable output transformations, allowing you to control which fields are included or excluded from the API responses. This is particularly useful for large responses like Graph Search results, where you might want to filter out unnecessary fields to reduce the payload size.

## Configuring Output Transformations

Output transformations are configured in the `output_transformation` section of your tool definition YAML file. You can also override or extend this configuration in your payload when executing a tool.

### Tool Definition Configuration

To add an output transformation to a tool definition, configure the `output_transformation` section in your YAML file:

```yaml
gql_mapping:
  query_name: graphSearch
  input_mapping:
    # ... input mapping configuration ...
  output_transformation:
    # Set to true to disable output transformation
    disabled: false

    # Global transformation options
    max_array_size: 100  # Limit all arrays to max 100 items
    max_text_length: 1000  # Limit all text fields to max 1000 characters

    # Field-specific array limits
    field_array_limits:
      "graphSearch.nodes": 50  # Limit the nodes array to 50 items
      "graphSearch.nodes.entities.technologies": 10  # Limit technologies array to 10 items

    # Field-specific text limits
    field_text_limits:
      "graphSearch.nodes.entities.properties.description": 200  # Limit description to 200 chars

    # Keep only boolean fields from these paths
    keep_only_boolean_paths:
      - securityControls
      - tags

    # Keep only these fields
    keep_only_fields:
      - graphSearch.totalCount
      - graphSearch.pageInfo.endCursor
      - graphSearch.nodes.entities.id
      - graphSearch.nodes.entities.name
      - graphSearch.nodes.entities.type
```

### Payload Override

You can override or extend the default output transformation in your payload file:

```yaml
# Your regular tool parameters
query:
  type: "VM"
limit: 5

# Override the default output transformation
output_transformation:
  max_array_size: 10
  keep_only_fields:
    - graphSearch.totalCount
    - graphSearch.nodes.entities.id
    - graphSearch.nodes.entities.name
    - graphSearch.nodes.entities.properties.operatingSystem
```

## Disabling Output Transformation

You can disable output transformation by setting the `disabled` flag to `true`:

```yaml
output_transformation:
  disabled: true
```

This is useful if you want to see the raw response from the API without any transformations.

## Transformation Options

The output transformation system supports several options:

### Field Filtering

You can filter fields in two ways:

1. **Keep only specific fields** (`keep_only_fields`):

```yaml
output_transformation:
  keep_only_fields:
    - graphSearch.totalCount
    - graphSearch.nodes.entities.id
    - graphSearch.nodes.entities.name
```

This will keep only the specified fields and remove all others from the response.

2. **Remove specific fields** (`remove_fields`):

```yaml
output_transformation:
  remove_fields:
    - graphSearch.nodes.entities.properties.tags
    - graphSearch.nodes.entities.technologies
```

This will remove the specified fields from the response.

**Using both keep_only_fields and remove_fields**: You can use both options together! When both are specified, `keep_only_fields` is applied first to select only the fields you want, then `remove_fields` is applied to remove specific fields from that result. This gives you precise control over the output format.

### Array Size Limiting

You can limit the size of arrays in the response in two ways:

1. **Global array size limit** (`max_array_size`):

```yaml
output_transformation:
  max_array_size: 10
```

This will limit all arrays in the response to a maximum of 10 items.

2. **Field-specific array limits** (`field_array_limits`):

```yaml
output_transformation:
  field_array_limits:
    "graphSearch.nodes": 5  # Limit the nodes array to 5 items
    "graphSearch.nodes.entities.technologies": 3  # Limit technologies array to 3 items
```

This will apply specific limits to the specified fields, while using the global limit (if specified) for all other arrays.

### Text Length Limiting

You can limit the length of text fields in the response in two ways:

1. **Global text length limit** (`max_text_length`):

```yaml
output_transformation:
  max_text_length: 100
```

This will limit all text fields in the response to a maximum of 100 characters.

2. **Field-specific text limits** (`field_text_limits`):

```yaml
output_transformation:
  field_text_limits:
    "graphSearch.nodes.entities.properties.description": 50  # Limit description to 50 chars
    "graphSearch.nodes.entities.properties.notes": 20  # Limit notes to 20 chars
```

This will apply specific limits to the specified fields, while using the global limit (if specified) for all other text fields.

### Boolean Field Extraction

You can keep only boolean fields from specific paths in the response:

```yaml
output_transformation:
  keep_only_boolean_paths:
    - securityControls
    - tags
```

This will keep only the boolean fields from the specified paths and remove all other fields from those paths.

## Error Handling

The output transformation system includes robust error handling to ensure that transformations don't fail even when the response doesn't match the expected format or contains errors:

- If the GraphQL response contains errors, the transformation is skipped and the original response is returned
- If a field specified in the transformation configuration doesn't exist in the response, it's simply ignored
- All errors are logged with appropriate warning or error level messages

This ensures that the transformation is resilient to unexpected response formats and won't cause the entire request to fail.

## Example

Here's a complete example of using output transformations:

1. Tool definition (in `your_tool.yaml`):

```yaml
name: your_tool
description: Your tool description
gql_query: |
  query YourQuery {
    # Your GraphQL query
  }

# ... other tool configuration ...

gql_mapping:
  query_name: graphSearch
  input_mapping:
    # ... input mapping configuration ...
  output_transformation:
    max_array_size: 100
    max_text_length: 1000
    keep_only_boolean_paths:
      - securityControls
    keep_only_fields:
      - graphSearch.totalCount
      - graphSearch.nodes.entities.id
      - graphSearch.nodes.entities.name
```

2. Payload file (in `your_payload.yaml`):

```yaml
query:
  type: "VM"
limit: 5
project_id: "*"

output_transformation:
  keep_only_fields:
    - graphSearch.totalCount
    - graphSearch.nodes.entities.id
    - graphSearch.nodes.entities.name
    - graphSearch.nodes.entities.properties.operatingSystem
    - graphSearch.nodes.entities.properties.osVersion
```

3. Execute the tool:

```bash
WIZ_DOTENV_PATH=/path/to/your/.env python src/wiz_mcp_server/server.py --execute-tool your_tool --payload your_payload.yaml
```

The result will include only the specified fields, making the response more compact and focused on the data you need.
