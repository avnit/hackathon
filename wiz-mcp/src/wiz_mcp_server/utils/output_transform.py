"""
Output Transformation Utilities for the Wiz MCP Server.

This module provides utility functions for transforming JSON responses
based on output mapping configurations.
"""

import copy
from typing import Dict, Any, List, Optional, Tuple, Callable

from wiz_mcp_server.utils.logger import get_logger

logger = get_logger()


def get_value_at_path(data: Dict[str, Any], path: str) -> Tuple[Any, bool]:
    """
    Get a value from a nested dictionary using a dot-notation path.

    Args:
        data: The dictionary to search in
        path: The path to the value, using dot notation (e.g., 'a.b.c')

    Returns:
        A tuple of (value, found) where value is the value at the path and found is True if the path exists
    """
    if not path:
        return data, True

    if not isinstance(data, dict):
        return None, False

    parts = path.split('.') if '.' in path else [path]
    current = data

    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current[part]

    return current, True


def set_value_at_path(data: Dict[str, Any], path: str, value: Any) -> None:
    """
    Set a value in a nested dictionary using a dot-notation path.
    Creates intermediate dictionaries if they don't exist.

    Args:
        data: The dictionary to modify
        path: The path to set, using dot notation (e.g., 'a.b.c')
        value: The value to set
    """
    if not path:
        return

    parts = path.split('.') if '.' in path else [path]
    current = data

    # Navigate to the parent of the field to set
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set the value at the deepest level
    current[parts[-1]] = value


def delete_value_at_path(data: Dict[str, Any], path: str) -> bool:
    """
    Delete a value from a nested dictionary using a dot-notation path.

    Args:
        data: The dictionary to modify
        path: The path to delete, using dot notation (e.g., 'a.b.c')

    Returns:
        True if the value was deleted, False otherwise
    """
    if not path:
        return False

    parts = path.split('.') if '.' in path else [path]
    current = data

    # Navigate to the parent of the field to delete
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]

    # Delete the field if it exists
    if isinstance(current, dict) and parts[-1] in current:
        del current[parts[-1]]
        return True

    return False


def get_specific_limit(path: str, field_specific_limits: Dict[str, int], match_type: str = 'endswith') -> Optional[int]:
    """
    Get a specific limit for a path from field-specific limits.

    Args:
        path: The current path
        field_specific_limits: Dictionary mapping field paths to their specific limits
        match_type: How to match the path ('exact', 'endswith', or 'startswith')

    Returns:
        The specific limit if found, None otherwise
    """
    if not field_specific_limits:
        return None

    for limit_path, limit in field_specific_limits.items():
        if match_type == 'exact' and path == limit_path:
            return limit
        elif match_type == 'endswith' and path.endswith(limit_path):
            logger.info(f"Found specific limit for path '{path}': {limit}")
            return limit
        elif match_type == 'startswith' and path.startswith(limit_path + '.'):
            return limit

    return None


def process_data_recursively(data: Any, processor: Callable, current_path: str = '', **kwargs) -> Any:
    """
    Process data recursively using a processor function.

    Args:
        data: The data to process
        processor: A function that processes a single value
        current_path: Current path in the data structure
        **kwargs: Additional arguments to pass to the processor

    Returns:
        The processed data
    """
    try:
        # Process the current value
        data = processor(data, current_path, **kwargs)

        # Recursively process children
        if isinstance(data, dict):
            return {k: process_data_recursively(v, processor, f"{current_path}.{k}" if current_path else k, **kwargs)
                    for k, v in data.items()}
        elif isinstance(data, list):
            return [process_data_recursively(item, processor, current_path, **kwargs)
                    for item in data]
        else:
            return data
    except Exception as e:
        logger.warning(f"Error processing data at path '{current_path}': {e}")
        return data


def transform_output(data: Dict[str, Any], output_mapping: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a JSON response based on the output mapping configuration.

    Args:
        data: The original JSON response
        output_mapping: The output mapping configuration

    Returns:
        The transformed response
    """
    # Check for errors in the response
    if not isinstance(data, dict):
        logger.warning(f"Cannot transform non-dict data: {type(data)}")
        return data

    # Check for our custom error format
    if 'error' in data and isinstance(data['error'], str):
        logger.warning(f"Error message in response, skipping transformation: {data['error']}")
        return data

    # Check for GraphQL errors
    if 'errors' in data:
        logger.warning(f"GraphQL errors in response, skipping transformation: {data['errors']}")
        return data

    if not output_mapping or output_mapping.get('disabled', False):
        return data

    try:
        # Create a deep copy to avoid modifying the original data
        result = copy.deepcopy(data)

        # Apply field filtering
        # First keep only specified fields if specified
        keep_only_fields = output_mapping.get('keep_only_fields')
        if keep_only_fields:
            result = filter_include_fields(result, keep_only_fields)

        # Then remove specified fields if specified (can be applied after keep_only_fields)
        remove_fields = output_mapping.get('remove_fields')
        if remove_fields:
            result = filter_exclude_fields(result, remove_fields)

        # Apply array size limiting
        max_array_size = output_mapping.get('max_array_size')
        field_array_limits = output_mapping.get('field_array_limits')
        if max_array_size or field_array_limits:
            result = limit_array_sizes(result, max_array_size or 100, field_array_limits)

        # Apply text length limiting
        max_text_length = output_mapping.get('max_text_length')
        field_text_limits = output_mapping.get('field_text_limits')
        if max_text_length or field_text_limits:
            result = limit_text_length(result, max_text_length or 1000, field_text_limits)

        # Keep only boolean fields at specified paths
        keep_only_boolean_paths = output_mapping.get('keep_only_boolean_paths')
        if keep_only_boolean_paths:
            result = keep_only_boolean_fields(result, keep_only_boolean_paths)

        # Preserve debug information
        for debug_field in ['_debug_variables', '_debug_query', '_debug_tool_name', '_context']:
            if debug_field in data:
                result[debug_field] = data[debug_field]

        return result
    except Exception as e:
        logger.error(f"Error transforming output: {e}")
        # Return the original data if transformation fails
        return data


def filter_include_fields(data: Dict[str, Any], include_paths: List[str]) -> Dict[str, Any]:
    """
    Filter the data to include only the specified fields.

    Args:
        data: The data to filter
        include_paths: List of paths to include (supports dot notation)

    Returns:
        The filtered data
    """
    if not include_paths:
        return data

    result = {}

    for path in include_paths:
        try:
            value, found = get_value_at_path(data, path)
            if found:
                set_value_at_path(result, path, value)
        except Exception as e:
            logger.warning(f"Error including field '{path}': {e}")
            continue

    return result


def filter_exclude_fields(data: Dict[str, Any], exclude_paths: List[str]) -> Dict[str, Any]:
    """
    Filter the data to exclude the specified fields.

    Args:
        data: The data to filter
        exclude_paths: List of paths to exclude (supports dot notation)

    Returns:
        The filtered data
    """
    if not exclude_paths:
        return data

    # Create a deep copy of the data to avoid modifying the original
    result = copy.deepcopy(data)

    for path in exclude_paths:
        try:
            delete_value_at_path(result, path)
        except Exception as e:
            logger.warning(f"Error excluding field '{path}': {e}")
            continue

    return result


def limit_array_processor(data: Any, current_path: str, max_size: int,
                          field_specific_limits: Dict[str, int] = None) -> Any:
    """
    Processor function for limiting array sizes.

    Args:
        data: The data to process
        current_path: Current path in the data structure
        max_size: The maximum size for arrays (global limit)
        field_specific_limits: Dictionary mapping field paths to their specific limits

    Returns:
        The processed data
    """
    if not isinstance(data, list):
        return data

    # Get specific limit for this path
    specific_limit = get_specific_limit(current_path, field_specific_limits, 'endswith')
    current_max_size = specific_limit if specific_limit is not None else max_size

    if specific_limit is not None and len(data) > current_max_size:
        logger.info(f"Limiting array at path '{current_path}' from {len(data)} to {current_max_size} items")

    return data[:current_max_size]


def limit_array_sizes(data: Any, max_size: int, field_specific_limits: Dict[str, int] = None) -> Any:
    """
    Limit the size of arrays in the data.

    Args:
        data: The data to process
        max_size: The maximum size for arrays (global limit)
        field_specific_limits: Dictionary mapping field paths to their specific limits

    Returns:
        The processed data
    """
    return process_data_recursively(
        data,
        limit_array_processor,
        max_size=max_size,
        field_specific_limits=field_specific_limits
    )


def text_length_processor(data: Any, current_path: str, max_length: int,
                          field_specific_limits: Dict[str, int] = None) -> Any:
    """
    Processor function for limiting text length.

    Args:
        data: The data to process
        current_path: Current path in the data structure
        max_length: The maximum length for text fields (global limit)
        field_specific_limits: Dictionary mapping field paths to their specific limits

    Returns:
        The processed data
    """
    if not isinstance(data, str):
        return data

    # Get specific limit for this path
    specific_limit = get_specific_limit(current_path, field_specific_limits, 'startswith')
    current_max_length = specific_limit if specific_limit is not None else max_length

    if len(data) > current_max_length:
        return data[:current_max_length] + '...'

    return data


def limit_text_length(data: Any, max_length: int, field_specific_limits: Dict[str, int] = None) -> Any:
    """
    Limit the length of text fields in the data.

    Args:
        data: The data to process
        max_length: The maximum length for text fields (global limit)
        field_specific_limits: Dictionary mapping field paths to their specific limits

    Returns:
        The processed data
    """
    return process_data_recursively(
        data,
        text_length_processor,
        max_length=max_length,
        field_specific_limits=field_specific_limits
    )


def keep_only_boolean_fields(data: Any, paths: List[str]) -> Any:
    """
    Keep only boolean fields from the data at the specified paths, removing all other fields.

    Args:
        data: The data to process
        paths: List of paths to keep only boolean fields from (supports dot notation)

    Returns:
        The processed data with only boolean fields kept at the specified paths
    """
    if not paths:
        return data

    # Create a deep copy of the data to avoid modifying the original
    result = copy.deepcopy(data)

    for path in paths:
        try:
            # Get the source dictionary
            source_dict, found = get_value_at_path(data, path)

            if found and isinstance(source_dict, dict):
                # Extract boolean fields
                bool_fields = {
                    k: v for k, v in source_dict.items()
                    if isinstance(v, (str, bool)) and str(v).lower() in ["true", "false"]
                }

                # Set the filtered dictionary in the result
                if bool_fields:
                    set_value_at_path(result, path, bool_fields)
                else:
                    # If no boolean fields were found, remove the path
                    delete_value_at_path(result, path)
        except Exception as e:
            logger.warning(f"Error extracting boolean fields from '{path}': {e}")
            continue

    return result
