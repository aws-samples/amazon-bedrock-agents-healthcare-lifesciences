"""Shared hub core — schema discovery (and, later, query execution) reused by the agent + MCP server."""
from .schema import get_hub_schema

__all__ = ["get_hub_schema"]
