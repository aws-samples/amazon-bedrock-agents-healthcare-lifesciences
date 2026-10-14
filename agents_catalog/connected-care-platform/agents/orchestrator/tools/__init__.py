"""Orchestrator Agent Tools"""

from .invoke_patient_monitoring import invoke_patient_monitoring
from .invoke_device_management import invoke_device_management
from .invoke_patient_engagement import invoke_patient_engagement
from .invoke_inventory_management import invoke_inventory_management
from .invoke_field_service import invoke_field_service
from .invoke_account_intelligence import invoke_account_intelligence
from .execute_workflow import execute_workflow
from .publish_workflow_event import publish_workflow_event

ALL_TOOLS = [
    invoke_patient_monitoring,
    invoke_device_management,
    invoke_patient_engagement,
    invoke_inventory_management,
    invoke_field_service,
    invoke_account_intelligence,
    execute_workflow,
    publish_workflow_event,
]
