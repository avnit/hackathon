# Creating and Testing Custom Tools

This guide explains how to create your own custom tools for the Wiz MCP Server and test them using the execute tool command.

## Overview

The Wiz MCP Server supports dynamic tool registration, which allows you to define tools in a declarative way using YAML files. This means you can create new tools without writing any Python code - you just need to know:

1. Which GraphQL query you want to run
2. Which parameters you want to expose to users
3. How to map those parameters to the GraphQL query variables

## Creating a New Tool

To create a new tool, you need to create a YAML file in the `src/wiz_mcp_server/tools/tool_definitions` directory. The file should follow this structure:

```yaml
name: your_tool_name
description: A clear description of what your tool does

# GraphQL query definition
gql_query: |
  query YourQuery($param1: Type1!, $param2: Type2) {
    someQuery(param1: $param1, param2: $param2) {
      field1
      field2
      # ... other fields you want to return
    }
  }

# GraphQL mapping definitions
gql_mapping:
  query_name: someQuery
  input_mapping:
    user_param1:
      path: param1
      description: "Description of user_param1"
    user_param2:
      path: param2
      description: "Description of user_param2"
  output_mapping:
    result_field1: field1
    result_field2: field2

# Input parameter definitions
input_params:
  user_param1:
    type: string
    description: "Description of user_param1"
    required: true
  user_param2:
    type: integer
    description: "Description of user_param2"
    default: 10
    required: false

# Default variables (optional)
default_variables:
  param1: "default_value"
  param2: 10
```

### Key Components

1. **name**: The name of your tool (used to invoke it)
2. **description**: A clear description of what your tool does
3. **gql_query**: The GraphQL query to execute
4. **gql_mapping**: Maps user parameters to GraphQL variables and defines output mapping
5. **input_params**: Defines the parameters that users can provide
6. **default_variables**: Optional default values for GraphQL variables

## Example: Creating a Tool to Get Kubernetes Clusters

Let's create a tool that retrieves Kubernetes clusters from Wiz:

```yaml
name: get_kubernetes_clusters
description: Retrieve Kubernetes clusters from Wiz with optional filtering

# GraphQL query definition
gql_query: |
  query KubernetesClusters($first: Int, $filterBy: KubernetesClusterFilters) {
    kubernetesClustersList(first: $first, filterBy: $filterBy) {
      nodes {
        id
        name
        cloudProvider
        region
        status
        version
        nodeCount
        createdAt
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }

# GraphQL mapping definitions
gql_mapping:
  query_name: kubernetesClustersList
  input_mapping:
    limit:
      path: first
      description: "Maximum number of clusters to return"
    cloud_provider:
      path: filterBy.cloudProvider
      description: "Filter by cloud provider"
    status:
      path: filterBy.status
      description: "Filter by cluster status"
  output_mapping:
    clusters:
      path: nodes[]
      fields:
        id: id
        name: name
        cloud_provider: cloudProvider
        region: region
        status: status
        version: version
        node_count: nodeCount
        created_at: createdAt
    page_info:
      path: pageInfo
      fields:
        has_next_page: hasNextPage
        end_cursor: endCursor
    total_count: totalCount

# Input parameter definitions
input_params:
  limit:
    type: integer
    description: "Maximum number of clusters to return"
    default: 50
    minimum: 1
    maximum: 1000
    required: false
  cloud_provider:
    type: string
    description: "Filter by cloud provider (AWS, GCP, AZURE)"
    required: false
    enum: ["AWS", "GCP", "AZURE"]
  status:
    type: string
    description: "Filter by cluster status (ACTIVE, INACTIVE)"
    required: false
    enum: ["ACTIVE", "INACTIVE"]

# Default variables
default_variables:
  first: 50
```

Save this file as `src/wiz_mcp_server/tools/tool_definitions/get_kubernetes_clusters.yaml`.

## Testing Your Tool

Once you've created your tool definition, you can test it without restarting the server by using the `execute-tool` command. This allows you to quickly iterate and refine your tool.

### 1. Create a Test Payload

Create a YAML file with the parameters you want to pass to your tool:

```yaml
# examples/get_kubernetes_clusters_payload.yaml
limit: 10
cloud_provider: "AWS"
```

### 2. Execute the Tool

Run the following command to execute your tool with the test payload:

```bash
WIZ_DOTENV_PATH=/path/to/your/.env uv run --with mcp[cli] python src/wiz_mcp_server/server.py --execute-tool get_kubernetes_clusters --payload examples/get_kubernetes_clusters_payload.yaml
```

Or directly with Python:

```bash
WIZ_DOTENV_PATH=/path/to/your/.env python src/wiz_mcp_server/server.py --execute-tool get_kubernetes_clusters --payload examples/get_kubernetes_clusters_payload.yaml
```

This will:
1. Load your tool definition
2. Authenticate with the Wiz API
3. Execute the GraphQL query with your parameters
4. Return the results

### 3. Iterating and Refining

If you need to make changes to your tool definition:

1. Edit the YAML file
2. Run the execute-tool command again
3. Repeat until you're satisfied with the results

There's no need to restart the server or rebuild anything - the tool definition is loaded dynamically each time.

## Advanced Features

### Nested Parameters

You can define nested parameters using dot notation in the `path` field:

```yaml
input_mapping:
  filter_name:
    path: filterBy.name
    description: "Filter by name"
```

This will map the `filter_name` parameter to `filterBy.name` in the GraphQL variables.

### Complex Filters

For complex filters, you can use nested structures in your payload:

```yaml
# examples/complex_filter_payload.yaml
filter:
  name: "production"
  status: "ACTIVE"
  tags:
    - key: "environment"
      value: "production"
```

### Output Transformations

For tools that return large result sets, you can configure output transformations in the `output_transformation` section to control which fields are included or excluded from the response:

```yaml
# Tool definition
gql_mapping:
  query_name: graphSearch
  input_mapping:
    # ... input mapping configuration ...
  output_transformation:
    # Global transformation options
    max_array_size: 100  # Limit all arrays to max 100 items
    max_text_length: 1000  # Limit all text fields to max 1000 characters

    # Field-specific limits
    field_array_limits:
      "graphSearch.nodes": 50  # Limit nodes array to 50 items
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

You can also override or extend the default output transformation in your payload:

```yaml
# examples/output_transformation.yaml
limit: 10
compact_mode: true
output_transformation:
  max_array_size: 10
  keep_only_fields:
    - graphSearch.totalCount
    - graphSearch.nodes.entities.id
    - graphSearch.nodes.entities.name
    - graphSearch.nodes.entities.properties.operatingSystem
```

This is especially useful for large responses, as it will reduce the payload size and make it more manageable. For more details, see the [Output Transformation](output_transformation.md) guide.

## Contributing Your Tool

Once you've created and tested your tool, you can contribute it to the project:

1. Add your tool definition to the `src/wiz_mcp_server/tools/tool_definitions` directory
2. Add a test payload to the `examples` directory
3. Add an end-to-end test to `end_to_end_tests/e2e_test_tools.py`
4. Submit a pull request

## Tips for Creating Effective Tools

1. **Keep it focused**: Each tool should do one thing well
2. **Provide clear descriptions**: Make it easy for users to understand what your tool does
3. **Use sensible defaults**: Set reasonable default values for optional parameters
4. **Add validation**: Use min/max values and enums to validate user input
5. **Test thoroughly**: Make sure your tool works with different parameter combinations

## Troubleshooting

### Common Issues

1. **GraphQL errors**: Check that your query syntax is correct and that you're using the right field names
2. **Parameter mapping errors**: Ensure that your input_mapping paths match the variables in your GraphQL query
3. **Authentication errors**: Make sure you have valid Wiz API credentials

### Debugging

You can add debug information to your tool by setting the logging level to DEBUG:

```bash
export WIZ_LOG_LEVEL=DEBUG
WIZ_DOTENV_PATH=/path/to/your/.env uv run --with mcp[cli] python src/wiz_mcp_server/server.py --execute-tool your_tool_name --payload examples/your_payload.yaml
```

This will show more detailed information about the GraphQL query and variables being sent.

## Examples

Check out the existing tool definitions in the `src/wiz_mcp_server/tools/tool_definitions` directory for more examples:

- `execute_wiz_query.yaml`: A general-purpose tool for executing Wiz Graph Search queries
- `get_issues.yaml`: A tool for retrieving security issues
- `text_to_wiz_query.yaml`: A tool that converts natural language to Wiz Graph Search queries

These examples cover a range of use cases and can serve as templates for your own tools.
