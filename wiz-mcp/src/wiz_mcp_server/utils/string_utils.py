import re


def sanitize_string(value, default="sanitized"):
    """
    Sanitize a string for HTTP headers - ASCII printable chars only.
    """
    if not value:
        return ""

    # Convert to string if not already
    value = str(value) if not isinstance(value, str) else value

    # Replace newlines and tabs with spaces
    value = value.replace("\n", " ").replace("\t", " ")

    # Remove control characters and non-ASCII characters
    sanitized = re.sub(r'[\x00-\x1F\x7F]|[^\x20-\x7E]', '', value)

    # Collapse consecutive spaces
    sanitized = re.sub(r'\s+', ' ', sanitized)

    return sanitized.strip() or default
