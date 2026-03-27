"""Session context models for user authentication and authorization."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """User roles for access control"""
    PATIENT = "patient"
    SERVICE_REP = "service_rep"
    DOCTOR = "doctor"
    NURSE = "nurse"
    ADMIN = "admin"


class SessionContext(BaseModel):
    """
    Session context containing user information and authorization details.
    
    This context is provided by the application layer after authentication
    and is used for authorization and audit logging.
    """
    user_id: str = Field(..., description="Authenticated user identifier")
    user_role: UserRole = Field(..., description="User role for access control")
    active_member_id: Optional[str] = Field(None, description="Currently selected member/patient ID")
    session_id: Optional[str] = Field(None, description="Session identifier")
    auth_token: Optional[str] = Field(None, description="Authentication token for audit logging")
    
    @classmethod
    def from_dict(cls, data: dict) -> "SessionContext":
        """Create SessionContext from dictionary"""
        return cls(**data)
    
    def to_dict(self) -> dict:
        """Convert SessionContext to dictionary"""
        return self.model_dump(exclude_none=True)
