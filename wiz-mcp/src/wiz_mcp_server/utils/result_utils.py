"""
Result Utilities for the Wiz MCP Server.

This module provides utility functions for processing results from the Wiz API,
specifically for making Graph Search results more compact and easier to work with.
"""


def parse_entity(entity):
    """
    Parse an entity to create a slimmer version with only essential fields.

    Args:
        entity: The entity to parse

    Returns:
        A slimmed-down version of the entity
    """
    if entity is not None:
        base_entity = {
            'id': entity['id'],
            'name': entity['name'],
            'description': entity['properties'].get('description', ''),
            'external_id': entity['properties'].get('externalId', ''),
            'type': entity['type'],
        }
        bool_fields = {k: v for k, v in entity['properties'].items() if str(v).lower() in ["true", "false"]}
        base_entity['properties'] = bool_fields
        return base_entity
    else:
        return entity


def get_compact_graph_search_results(data):
    """
    Create a compact version of Wiz Graph Search results.

    This function takes the verbose Graph Search results from the Wiz API
    and transforms them into a more compact and easier-to-use format.

    Args:
        data: The GraphQL query results containing graphSearch data

    Returns:
        A compact version of the Graph Search results with entities and paths
    """
    if "graphSearch" not in data:
        # Not a Graph Search result, return unchanged
        return data

    paths = []
    entities = {}
    for x in data["graphSearch"]['nodes']:
        new_entities = [parse_entity(e) for e in x['entities']]
        for entity in new_entities:
            entities[entity['id']] = entity
        graph_paths = [x['id'] for x in new_entities]
        paths.append(graph_paths)

    return {
        "graph_entities": entities,
        "graph_paths": paths,
        'total_count': data["graphSearch"].get('totalCount', None),
        'fetched': data["graphSearch"].get("pageInfo", {}).get('endCursor', None),
        '_debug_variables': data.get('_debug_variables'),
        '_debug_query': data.get('_debug_query'),
        '_debug_tool_name': data.get('_debug_tool_name')
    }
