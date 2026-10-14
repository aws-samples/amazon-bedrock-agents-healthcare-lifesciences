"""Shared DynamoDB sanitizer — converts Decimal, set, bytes to JSON-safe types."""

from decimal import Decimal


def sanitize(obj):
    """Recursively convert DynamoDB types to JSON-serializable Python types."""
    if isinstance(obj, Decimal):
        return int(obj) if obj == int(obj) else float(obj)
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    return obj
