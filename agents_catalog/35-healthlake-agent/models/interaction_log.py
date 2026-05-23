"""Interaction log models for audit trail."""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class InteractionLog(BaseModel):
    """Log entry for agent interactions"""
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    query: str = Field(..., description="User query")
    response: Optional[str] = Field(None, description="Agent response")
    context: Optional[Dict[str, Any]] = Field(None, description="Session context")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp")
    error: Optional[str] = Field(None, description="Error message if any")
