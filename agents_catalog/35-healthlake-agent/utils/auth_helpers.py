"""Authorization helpers for access control."""

import logging

logger = logging.getLogger(__name__)


class AuthorizationError(Exception):
    """Raised when authorization fails"""
    pass


def validate_patient_scope(
    user_role: str,
    user_id: str,
    active_member_id: str = None
):
    """
    Validate that a patient user can only access their own data.
    
    Args:
        user_role: User role (patient, service_rep, doctor, nurse, admin)
        user_id: User identifier
        active_member_id: Currently selected member/patient ID
    
    Raises:
        AuthorizationError: If patient attempts to access another patient's records
    """
    # Patients can only access their own data
    if user_role == "patient":
        if active_member_id and active_member_id != user_id:
            logger.warning(
                f"Authorization denied: Patient {user_id} attempted to access "
                f"member {active_member_id}"
            )
            raise AuthorizationError(
                "Patients can only access their own medical records"
            )
    
    # Other roles (service_rep, doctor, nurse, admin) can access any patient
    logger.debug(f"Authorization granted: role={user_role}, user={user_id}")
