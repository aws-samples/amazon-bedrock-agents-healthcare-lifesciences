"""Agent response models."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """Response from the agent"""
    text: str = Field(..., description="Agent response text")
    session_id: str = Field(..., description="Session identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
