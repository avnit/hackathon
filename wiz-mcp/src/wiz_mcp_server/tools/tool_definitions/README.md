# Tool Definitions

This directory contains YAML files that define tools for the Wiz MCP Server. Each YAML file defines a single tool that
can be used to interact with the Wiz API.

## Creating and Testing Custom Tools

For a comprehensive guide on creating and testing your own tools, see
the [Creating and Testing Custom Tools](../../../../docs/creating_tools.md) guide. This guide includes:

- Step-by-step instructions for creating a new tool
- How to test your tool using the `--execute-tool` command
- Examples of different types of tools
- Tips for creating effective tools

## Quick Start

To create a new tool definition:

1. Create a new YAML file in this directory
2. Define the required fields: `name`, `description`, and `gql_query`
3. Define the input parameters and output mapping
4. Test your tool using the `--execute-tool` command

Example:

```bash
WIZ_DOTENV_PATH=/path/to/your/.env uv run --with mcp[cli] python src/wiz_mcp_server/server.py --execute-tool your_tool_name --payload examples/your_payload.yaml
```

Or directly with Python:

```bash
WIZ_DOTENV_PATH=/path/to/your/.env python src/wiz_mcp_server/server.py --execute-tool your_tool_name --payload examples/your_payload.yaml
```

## Tool Definition Fields

### Basic Fields

- `name`: The name of the tool
- `description`: A description of what the tool does
- `gql_query`: The GraphQL query to execute
- `disabled` (optional): Set to `true` to disable the tool (default: `false`)

### Input Parameters

The `input_params` section defines the parameters that can be passed to the tool. Each parameter has the following
fields:

- `type`: The type of the parameter (string, integer, boolean, array[string], object)
- `description`: A description of the parameter
- `required`: Whether the parameter is required (true/false)
- `default`: The default value for the parameter
- `allowed_values`: A list of allowed values for the parameter

Example:

```yaml
input_params:
  limit:
    type: integer
    description: Maximum number of results to return
    required: true
    default: 10
  status:
    type: array[string]
    description: Filter by status
    required: false
    allowed_values:
      - ACTIVE
      - INACTIVE
```

### GraphQL Mapping

The `gql_mapping` section defines how the tool's parameters are mapped to GraphQL variables. It has the following
fields:

- `query_name`: The name of the query in the GraphQL response
- `input_mapping`: Maps input parameters to GraphQL variables
- `output_mapping`: Maps GraphQL response fields to output fields

Example:

```yaml
gql_mapping:
  query_name: result
  input_mapping:
    limit: first
    search:
      path: filterBy.search
      description: Search term
  output_mapping:
    items:
      path: nodes[]
      fields:
        id: id
        name: name
    has_next_page: pageInfo.hasNextPage
    end_cursor: pageInfo.endCursor
```

### Output Fields

The `output_fields` section defines the structure of the tool's output. It has the following fields:

- `type`: The type of the field (string, integer, boolean, array[object], object)
- `description`: A description of the field
- `fields`: For array[object] and object types, defines the fields of the object

Example:

```yaml
output_fields:
  items:
    type: array[object]
    description: List of results
    fields:
      id:
        type: string
        description: Resource ID
      name:
        type: string
        description: Resource name
  has_next_page:
    type: boolean
    description: Whether there are more results available
```

### Advanced Fields

- `default_variables`: Default variables to include in every request
- `disabled`: Set to `true` to disable the tool without removing the file

Example:

```yaml
default_variables:
  orderBy:
    field: CREATED_AT
    direction: DESC

# Disable this tool without removing the file
# disabled: true
```

## Parameter Descriptions

When defining parameters, make sure to include detailed descriptions that help the LLM understand how to use them
correctly. A good description should include:

1. What the parameter does
2. The possible values (for enum types)
3. The expected format
4. An example

Example:

```yaml
severity:
  type: array[string]
  description: "Filter issues by severity level. Possible values: CRITICAL, HIGH, MEDIUM, LOW. Example: [\"HIGH\", \"CRITICAL\"]"
  required: false
  allowed_values:
    - CRITICAL
    - HIGH
    - MEDIUM
    - LOW
```

## Parameter Mapping

The `input_mapping` section defines how parameters are mapped to GraphQL variables. There are three types of mappings:

### 1. Direct Mapping

Maps a parameter directly to a GraphQL variable:

```yaml
input_mapping:
  first: first    # Maps 'first' parameter to 'first' GraphQL variable
  cursor: after   # Maps 'cursor' parameter to 'after' GraphQL variable
```

### 2. Simple FilterBy Mapping

Maps a parameter to a field in the filterBy object:

```yaml
input_mapping:
  severity:
    path: filterBy.severity
    description: "Filter issues by severity level. Possible values: CRITICAL, HIGH, MEDIUM, LOW."
```

This tells the system to place the `severity` parameter inside the `filterBy` object in the GraphQL variables.

### 3. Nested FilterBy Mapping

Maps a parameter to a nested field in the filterBy object:

```yaml
input_mapping:
  updated_after:
    path: filterBy.updatedAt.after
    description: "Filter resources updated after this datetime"
```

This creates a nested structure: `{ "filterBy": { "updatedAt": { "after": value } } }`

## Example Tool Definition

See the `get_issues.yaml` file for an example of a complete tool definition.
